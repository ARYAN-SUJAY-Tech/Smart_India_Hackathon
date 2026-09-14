"""
Two trained models, both wired in (Sep 2026 drop: ARYAN-SUJAY-Tech/Smart_India_Hackathon).

Contract unchanged at the top level: predict_risk(features) -> float in
[0, 1] plus explain_risk(features) -> dict. Routers/alerting never need
to change when either underlying model is swapped -- that's the point
of keeping this module as the single integration seam.

Model facts (verified by loading each .pkl directly):

  1. sikkim_landslide_rf_model.pkl
     feature_names_in_ = ['elevation', 'slope', 'soil_moisture']
     classes_ = [0, 1] -- class 1 = landslide-positive
     Feature importances: elevation 0.446, soil_moisture 0.350, slope 0.203

  2. sikkim_flood_model.pkl (feature order from sikkim_flood_model_features.pkl)
     features = ['elevation', 'max_rainfall', 'mean_rainfall', 'total_rainfall',
                 'slope', 'mean_soil_moisture', 'max_soil_moisture']
     classes_ = [0, 1] -- class 1 = flood-positive

Both take a pandas DataFrame with named columns, not a bare array.

Combining the two scores is a product decision, not a technical one:
we take risk_score = max(landslide_risk, flood_risk) since the PS asks
for a combined flash-flood-and-landslide warning and a village should
be flagged if EITHER hazard is elevated, not only when both agree.
Both individual scores are still exposed in contributing_factors so
nothing is hidden from the frontend or the demo.

mean_soil_moisture and max_soil_moisture both use the same single
"latest SMAP snapshot" value -- this mirrors the ML teammate's own
sikkim_predict_pipeline.py comment (there's no forecast product for
soil moisture the way there is for rainfall), not a shortcut we're
introducing independently.
"""
import joblib
import pandas as pd
from pathlib import Path
from typing import Dict

_ML_DIR = Path(__file__).resolve().parent.parent / "ml"
_LANDSLIDE_MODEL_PATH = _ML_DIR / "sikkim_landslide_rf_model.pkl"
_FLOOD_MODEL_PATH = _ML_DIR / "sikkim_flood_model.pkl"
_FLOOD_FEATURES_PATH = _ML_DIR / "sikkim_flood_model_features.pkl"

_LANDSLIDE_FEATURE_ORDER = ["elevation", "slope", "soil_moisture"]

_landslide_model = None
_flood_model = None
_flood_feature_order = None


def _get_landslide_model():
    global _landslide_model
    if _landslide_model is None:
        _landslide_model = joblib.load(_LANDSLIDE_MODEL_PATH)
    return _landslide_model


def _get_flood_model():
    global _flood_model, _flood_feature_order
    if _flood_model is None:
        _flood_model = joblib.load(_FLOOD_MODEL_PATH)
        _flood_feature_order = joblib.load(_FLOOD_FEATURES_PATH)
    return _flood_model, _flood_feature_order


def predict_landslide_risk(features: Dict[str, float]) -> float:
    """features: elevation, slope, soil_moisture. Missing keys default to 0."""
    model = _get_landslide_model()
    row = {k: features.get(k, 0.0) for k in _LANDSLIDE_FEATURE_ORDER}
    X = pd.DataFrame([row], columns=_LANDSLIDE_FEATURE_ORDER)
    proba = model.predict_proba(X)[0]
    return float(proba[1])


def predict_flood_risk(features: Dict[str, float]) -> float:
    """
    features: elevation, slope, max_rainfall, mean_rainfall, total_rainfall,
    mean_soil_moisture, max_soil_moisture. Missing keys default to 0.
    """
    model, feature_order = _get_flood_model()
    row = {k: features.get(k, 0.0) for k in feature_order}
    X = pd.DataFrame([row], columns=feature_order)
    proba = model.predict_proba(X)[0]
    return float(proba[1])


def predict_risk(features: Dict[str, float]) -> float:
    """
    Combined risk_score used by RiskOut. features must contain the union
    of both models' keys (see routers/risk.py's _latest_features()).
    """
    landslide_risk = predict_landslide_risk(features)
    flood_risk = predict_flood_risk(features)
    combined = max(landslide_risk, flood_risk)
    return round(max(0.0, min(combined, 1.0)), 3)


def explain_risk(features: Dict[str, float]) -> Dict[str, float]:
    """
    contributing_factors shown to the frontend/demo. Exposes both
    individual hazard scores plus the landslide model's real feature
    importances so the breakdown stays honest about what actually drove
    each number, not a guess.
    """
    landslide_model = _get_landslide_model()
    landslide_importances = dict(zip(
        landslide_model.feature_names_in_, landslide_model.feature_importances_
    ))

    elevation_norm = min(features.get("elevation", 0.0) / 2500.0, 1.0)
    slope_norm = min(features.get("slope", 0.0) / 60.0, 1.0)
    soil_moisture_norm = min(features.get("soil_moisture", 0.0) / 0.48, 1.0)

    raw = {
        "elevation": landslide_importances.get("elevation", 0.0) * elevation_norm,
        "slope": landslide_importances.get("slope", 0.0) * slope_norm,
        "soil_moisture": landslide_importances.get("soil_moisture", 0.0) * soil_moisture_norm,
    }
    total = sum(raw.values()) or 1.0
    landslide_breakdown = {k: round(v / total, 3) for k, v in raw.items()}

    return {
        "landslide_risk": round(predict_landslide_risk(features), 3),
        "flood_risk": round(predict_flood_risk(features), 3),
        **{f"landslide_{k}": v for k, v in landslide_breakdown.items()},
    }
