# Flood Watch — ML

Landslide risk model for the Flash Flood & Landslide Early Warning
System — SIH PS26192. Trains the Random Forest classifier that
`Backend/app/services/risk_model.py` loads at inference time.

## Data

- **`sikkim_landslide_dataset.csv`** — 210 labeled points over Sikkim
  (105 landslide-positive, 105 negative, perfectly balanced), each with
  `latitude, longitude, elevation, slope, aspect, curvature,
  soil_moisture, label`.
- **`Sikkim.tif`** — DEM tile for the region (bounding box in
  `sikkim_bbox.geojson`, roughly 88.19–88.81°E, 27.02–27.90°N). Source
  of `elevation`/`slope`/`aspect`/`curvature` for both the training
  points and, via `Backend/app/services/dem_processing.py`, real
  villages seeded into the backend.
- **`smap_data/`** — NASA SMAP (SPL3SMP_E) daily soil moisture retrieval
  rasters, 2022-01-01 through 2024-12-31. Source of the `soil_moisture`
  feature (range in the training set: ~0.20–0.48, a fraction not a
  percentage — the backend and frontend both assume that scale).

## Model

`train.py`:

1. Loads the CSV and splits into `features = [elevation, slope,
   soil_moisture]`, label, and lat/lon.
2. Groups points into 4 spatial zones via `KMeans` on coordinates, then
   runs **Leave-One-Group-Out spatial cross-validation** — holding out
   an entire geographic zone per fold, not a random point split. Random
   splits on spatially autocorrelated data (nearby points share
   conditions) overstate accuracy; holding out whole zones tests
   generalization to *unseen terrain*, which is what actually matters
   for predicting on a new village.
3. Trains the final `RandomForestClassifier` (200 trees, `max_depth=10`,
   `min_samples_leaf=3`, `class_weight="balanced"`) on all 210 points
   and dumps it to `sikkim_landslide_rf_model.pkl`.

`feature_importance.py` loads that model back and plots both MDI (Gini)
and permutation importance per feature to `feature_importance.png`.

**Locked contract with the backend** (`risk_model.py`'s `predict_risk`):
`feature_names_in_ = ["elevation", "slope", "soil_moisture"]`, in that
order, passed as a DataFrame with those column names — not a bare
array, since sklearn silently trusts column order over names otherwise.
`predict_proba()[:, 1]` (probability of class `1`, landslide-positive)
is the risk score. `aspect`/`curvature` are collected here but **not**
model inputs; don't bother wiring them through if you're integrating a
new data source.

## Reproducing

```bash
pip install pandas numpy scikit-learn joblib matplotlib
python train.py               # spatial CV report + writes sikkim_landslide_rf_model.pkl
python feature_importance.py  # writes feature_importance.png
```

Pin `scikit-learn` to whatever `train.py` was actually run with — the
committed `.pkl` was pickled under scikit-learn 1.9.1, and loading it
under a different version prints an `InconsistentVersionWarning` (see
`Backend/README.md`).

## Known limitations, on purpose

- **Rainfall isn't a feature.** `rainfall_mm` is collected by the
  backend on every sensor reading but not used here — the training
  data doesn't include it. Retrain with a rainfall column and update
  `_FEATURE_ORDER` in `Backend/app/services/risk_model.py` together if
  that changes.
- **Sikkim only.** The DEM tile, SMAP extent, and all 210 training
  points cover one state. Extending to other hilly regions means
  sourcing a new DEM + labeled inventory for that region, not just
  re-running `train.py`.
- **210 points total.** Small for a Random Forest; the spatial CV
  report from `train.py` is the honest generalization estimate, not the
  training-set accuracy.

## See also

- `../Backend/README.md` — how the API loads and serves this model.
- `../frontend/README.md` — how risk scores/levels reach the map UI.
- `../README.md` — full-system overview.
