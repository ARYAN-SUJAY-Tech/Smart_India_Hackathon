import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import LeaveOneGroupOut

# 1. Load extracted feature dataset
df = pd.read_csv("sikkim_landslide_dataset.csv")

# 2. Separate features, labels, and coordinates
features = ["elevation", "slope", "soil_moisture"]
X = df[features]
y = df["label"]
coords = df[["longitude", "latitude"]]

# 3. Spatial Grouping using KMeans
# Adjust n_clusters based on total spatial distribution
kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
groups = kmeans.fit_predict(coords)

print("Points per spatial zone:", np.bincount(groups))

# 4. Spatial Cross-Validation (Leave-One-Group-Out)
logo = LeaveOneGroupOut()
all_preds = np.zeros(len(y), dtype=int)
all_trues = np.zeros(len(y), dtype=int)
fold_scores = []

for fold, (train_idx, test_idx) in enumerate(logo.split(X, y, groups)):
    X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
    y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]

    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )
    clf.fit(X_tr, y_tr)

    preds = clf.predict(X_te)
    score = accuracy_score(y_te, preds)
    fold_scores.append(score)

    all_preds[test_idx] = preds
    all_trues[test_idx] = y_te
    print(f"Spatial Zone {fold} Held Out — Accuracy: {score * 100:.2f}%")

print(f"\n================ SPATIAL CV RESULTS ================")
print(f"Mean Spatial Accuracy: {np.mean(fold_scores) * 100:.2f}% (Std: {np.std(fold_scores) * 100:.2f}%)")
print("\nAggregated Classification Report:")
print(classification_report(all_trues, all_preds))

# 5. Train final model on ALL data and export
final_rf = RandomForestClassifier(
    n_estimators=200,
    max_depth=10,
    min_samples_leaf=3,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)
final_rf.fit(X, y)
joblib.dump(final_rf, "sikkim_landslide_rf_model.pkl")
print("\nFinal model saved to 'sikkim_landslide_rf_model.pkl'")