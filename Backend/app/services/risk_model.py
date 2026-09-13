"""
Real trained model, wired in (Sep 2026 drop from ML teammate's
Smart_India_Hackathon-main/ML/ repo: train.py + sikkim_landslide_rf_model.pkl).

Contract unchanged: predict_risk(features: dict) -> float in [0, 1]
Routers/alerting never needed to change for this swap -- exactly the
point of keeping this function as the single integration seam.

Model facts (verified by loading the .pkl directly):
  - RandomForestClassifier, 200 trees, spatial CV via LeaveOneGroupOut
  - feature_names_in_ = ['elevation', 'slope', 'soil_moisture'], in
    that exact order -- must pass a DataFrame with these column names,
    not a bare array, or sklearn raises a "no feature names" warning
    and (worse) silently trusts column ORDER instead of names if you
    ever pass a differently-ordered array.
  - classes_ = [0, 1] -- class 1 is landslide-positive; predict_proba()
    column 1 is our risk score.
  - Feature importances (real, from the trained model):
        elevation:      0.446
        soil_moisture:  0.350
        slope:          0.203
  - aspect/curvature exist in his training CSV but are NOT used by
    the model -- do not bother sourcing/passing them.
  - rainfall is STILL not a feature. Unchanged from earlier: either
    he adds it later (re-train, we re-integrate), or it stays as a
    rule in alerting.py, independent of this model.

Environment note: model was pickled under scikit-learn 1.9.1. If your
venv has a different version, joblib.load will emit an
InconsistentVersionWarning (harmless for RandomForest structure, but
flag it to the ML teammate if you see prediction drift). Pin
scikit-learn to match his training environment where possible.
"""
import joblib
import pandas as pd
from pathlib import Path
from typing import Dict

_MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "sikkim_landslide_rf_model.pkl"
_FEATURE_ORDER = ["elevation", "slope", "soil_moisture"]

_model = None


def _get_model():
    """Lazy-load once per process, not per request."""
    global _model
    if _model is None:
        _model = joblib.load(_MODEL_PATH)
    return _model


def predict_risk(features: Dict[str, float]) -> float:
    """
    features must contain (missing keys default to 0.0, which will
    generally under-predict risk rather than crash -- fine for a
    prototype, but log a warning if this happens in real ingestion):
        - elevation      (meters)
        - slope          (degrees)
        - soil_moisture  (fraction, ~0.2-0.48 per his training data)
    """
    model = _get_model()
    row = {k: features.get(k, 0.0) for k in _FEATURE_ORDER}
    X = pd.DataFrame([row], columns=_FEATURE_ORDER)
    proba = model.predict_proba(X)[0]
    # classes_ = [0, 1] -- index 1 is landslide-positive probability
    risk_score = float(proba[1])
    return round(max(0.0, min(risk_score, 1.0)), 3)


def explain_risk(features: Dict[str, float]) -> Dict[str, float]:
    """
    Approximate per-factor contribution using the model's REAL feature
    importances (not a guess) weighted by how "activated" each feature
    is for this village, normalized against the training data's
    observed ranges. This is a display aid for contributing_factors,
    not a SHAP-level explanation -- fine for a hackathon demo table.
    """
    model = _get_model()
    importances = dict(zip(model.feature_names_in_, model.feature_importances_))

    # rough normalization ranges from the training dataset
    # (elevation ~450-2500m, slope 0-60deg, soil_moisture 0.2-0.48)
    elevation_norm = min(features.get("elevation", 0.0) / 2500.0, 1.0)
    slope_norm = min(features.get("slope", 0.0) / 60.0, 1.0)
    soil_moisture_norm = min(features.get("soil_moisture", 0.0) / 0.48, 1.0)

    raw = {
        "elevation": importances.get("elevation", 0.0) * elevation_norm,
        "slope": importances.get("slope", 0.0) * slope_norm,
        "soil_moisture": importances.get("soil_moisture", 0.0) * soil_moisture_norm,
    }
    total = sum(raw.values()) or 1.0
    return {k: round(v / total, 3) for k, v in raw.items()}
