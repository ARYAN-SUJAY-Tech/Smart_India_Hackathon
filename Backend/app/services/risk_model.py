"""
Real trained model, wired in. Now using the new sikkim_flood_model.pkl from ML teammate's repo,
which includes rainfall and updated soil moisture features.
"""
import joblib
import pandas as pd
from pathlib import Path
from typing import Dict

_MODEL_PATH = Path(__file__).resolve().parent.parent.parent.parent / "ML" / "sikkim_flood_model.pkl"
_FEATURE_ORDER = [
    "elevation", "max_rainfall", "mean_rainfall", "total_rainfall", 
    "slope", "mean_soil_moisture", "max_soil_moisture"
]

_model = None


def _get_model():
    """Lazy-load once per process, not per request."""
    global _model
    if _model is None:
        _model = joblib.load(_MODEL_PATH)
    return _model


def predict_risk(features: Dict[str, float]) -> float:
    """
    features must contain:
        - elevation
        - max_rainfall
        - mean_rainfall
        - total_rainfall
        - slope
        - mean_soil_moisture
        - max_soil_moisture
    """
    model = _get_model()
    row = {k: features.get(k, 0.0) for k in _FEATURE_ORDER}
    X = pd.DataFrame([row], columns=_FEATURE_ORDER)
    proba = model.predict_proba(X)[0]
    # classes_ = [0, 1] -- index 1 is positive probability
    risk_score = float(proba[1])
    return round(max(0.0, min(risk_score, 1.0)), 3)


def explain_risk(features: Dict[str, float]) -> Dict[str, float]:
    """
    Approximate per-factor contribution.
    """
    model = _get_model()
    importances = dict(zip(model.feature_names_in_, model.feature_importances_))

    # rough normalization ranges
    elevation_norm = min(features.get("elevation", 0.0) / 2500.0, 1.0)
    slope_norm = min(features.get("slope", 0.0) / 60.0, 1.0)
    mean_sm_norm = min(features.get("mean_soil_moisture", 0.0) / 0.48, 1.0)
    max_sm_norm = min(features.get("max_soil_moisture", 0.0) / 0.48, 1.0)
    total_rain_norm = min(features.get("total_rainfall", 0.0) / 200.0, 1.0)
    mean_rain_norm = min(features.get("mean_rainfall", 0.0) / 100.0, 1.0)
    max_rain_norm = min(features.get("max_rainfall", 0.0) / 150.0, 1.0)

    raw = {
        "elevation": importances.get("elevation", 0.0) * elevation_norm,
        "slope": importances.get("slope", 0.0) * slope_norm,
        "mean_soil_moisture": importances.get("mean_soil_moisture", 0.0) * mean_sm_norm,
        "max_soil_moisture": importances.get("max_soil_moisture", 0.0) * max_sm_norm,
        "total_rainfall": importances.get("total_rainfall", 0.0) * total_rain_norm,
        "mean_rainfall": importances.get("mean_rainfall", 0.0) * mean_rain_norm,
        "max_rainfall": importances.get("max_rainfall", 0.0) * max_rain_norm,
    }
    total = sum(raw.values()) or 1.0
    return {k: round(v / total, 3) for k, v in raw.items()}
