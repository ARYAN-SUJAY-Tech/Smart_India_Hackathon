import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

# 1. Load data and saved model
df = pd.read_csv("sikkim_landslide_dataset.csv")
rf_model = joblib.load("sikkim_landslide_rf_model.pkl")

features = ["elevation", "slope", "soil_moisture"]
X = df[features]
y = df["label"]

# 2. Extract Mean Decrease in Impurity (MDI) importances & standard deviations
importances = rf_model.feature_importances_
std = np.std([tree.feature_importances_ for tree in rf_model.estimators_], axis=0)

# 3. Calculate Permutation Importance (Out-of-Bag robust metric)
perm_result = permutation_importance(
    rf_model, X, y, n_repeats=10, random_state=42, n_jobs=-1
)

# Build summary DataFrame
fi_df = pd.DataFrame({
    "Feature": features,
    "MDI_Importance": importances,
    "MDI_Std": std,
    "Permutation_Importance": perm_result.importances_mean,
    "Permutation_Std": perm_result.importances_std
}).sort_values(by="MDI_Importance", ascending=True)

# 4. Plot Dual Feature Importance (MDI vs Permutation)
fig, ax = plt.subplots(figsize=(9, 4.5), dpi=300)

y_pos = np.arange(len(features))
height = 0.35

ax.barh(y_pos - height/2, fi_df["MDI_Importance"], height, xerr=fi_df["MDI_Std"], 
        label="MDI (Gini Importance)", color="#2b5c8f", capsize=4, alpha=0.9)

ax.barh(y_pos + height/2, fi_df["Permutation_Importance"], height, xerr=fi_df["Permutation_Std"], 
        label="Permutation Importance", color="#d95f02", capsize=4, alpha=0.9)

ax.set_yticks(y_pos)
ax.set_yticklabels(fi_df["Feature"], fontsize=10, fontweight="bold")
ax.set_xlabel("Relative Importance Score", fontsize=10, labelpad=8)
ax.set_title("Sikkim Landslide Model: Feature Importance Metrics", fontsize=12, fontweight="bold", pad=12)
ax.legend(loc="lower right")
ax.grid(axis="x", linestyle="--", alpha=0.5)

plt.tight_layout()
plt.savefig("feature_importance.png")
plt.show()

print("Feature importance chart successfully saved as 'feature_importance.png'")