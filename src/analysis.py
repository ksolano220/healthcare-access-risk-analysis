"""
Healthcare Access Risk Analysis

Scores US counties by healthcare access risk using uninsured rates
and hospital density. Outputs ranked CSVs and a scatterplot.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

Path("outputs").mkdir(exist_ok=True)

# Load data
df = pd.read_csv("data/healthcare_data.csv", dtype={"fips": str})

# Derived metrics
df["uninsured_rate"] = df["uninsured_population"] / df["total_population"] * 100
df["hospitals_per_100k"] = df["hospital_count"] / df["total_population"] * 100_000

# Standardize (z-scores)
df["uninsured_z"] = (df["uninsured_rate"] - df["uninsured_rate"].mean()) / df["uninsured_rate"].std()
df["hospitals_z"] = (df["hospitals_per_100k"] - df["hospitals_per_100k"].mean()) / df["hospitals_per_100k"].std()

# Access risk: high uninsured + low hospital density = high risk
df["access_risk_score"] = df["uninsured_z"] - df["hospitals_z"]

# Priority score: risk-weighted with population factor
df["estimated_patient_load"] = df["total_population"] * 0.1
df["priority_score"] = (
    df["access_risk_score"] * 0.6
    + df["estimated_patient_load"] * 0.00001
)

# Rank
df["priority_rank"] = df["priority_score"].rank(ascending=False, method="dense").astype(int)

# Risk tier
df["risk_tier"] = pd.cut(
    df["access_risk_score"],
    bins=[-float("inf"), -0.5, 0.5, 1.5, float("inf")],
    labels=["Low", "Moderate", "High", "Critical"],
)

# Save outputs
priority_df = df.sort_values("priority_score", ascending=False)
priority_df.to_csv("outputs/priority_ranking.csv", index=False)

top_risk = df.sort_values("access_risk_score", ascending=False)
top_risk.to_csv("outputs/top_risk_counties.csv", index=False)

# Summary stats
print(f"Counties analyzed: {len(df)}")
print(f"\nRisk tier distribution:")
print(df["risk_tier"].value_counts().sort_index())
print(f"\nTop 10 highest-risk counties:")
print(top_risk[["county", "state", "access_risk_score", "risk_tier"]].head(10).to_string(index=False))

# Scatterplot
fig, ax = plt.subplots(figsize=(10, 6))
colors = df["access_risk_score"]
scatter = ax.scatter(
    df["hospitals_per_100k"],
    df["uninsured_rate"],
    c=colors,
    cmap="RdYlGn_r",
    alpha=0.5,
    s=12,
    edgecolors="none",
)
plt.colorbar(scatter, label="Access Risk Score")
ax.set_xlabel("Hospitals per 100k Population")
ax.set_ylabel("Uninsured Rate (%)")
ax.set_title("Healthcare Access Risk by County")
plt.tight_layout()
plt.savefig("outputs/scatterplot.png", dpi=150)
plt.close()

print("\nOutputs saved to outputs/")
