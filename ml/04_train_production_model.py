"""
Step 4: Train a "production" model using only the features that the live
TrafficVision AI system actually collects (vehicle count, speed, occupancy,
accident flag, weather condition, and time-derived features) -- as opposed to
the full Kaggle dataset, which includes fields like sentiment, ride-sharing
demand, and emissions that this system has no way to supply at inference time.

Weather is included because it's operationally available (an operator can
select current conditions, or it can later be pulled from a weather API),
even though EDA showed it has near-zero correlation with congestion in this
particular dataset -- see eda/EDA_SUMMARY.md and the weather crosstab. It's
kept in for completeness / matching the full feature set, with that caveat
documented rather than silently dropped.

Usage:
    python 04_train_production_model.py
"""

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

PROCESSED_DATA_PATH = "data/processed_traffic_data.csv"
MODEL_OUTPUT_PATH = "models/congestion_model_production.joblib"
TARGET_ENCODER_PATH = "models/target_encoder_production.joblib"

TARGET_COLUMN = "Traffic_Condition"

# Only features the live system can actually supply at prediction time.
# Weather_Condition is already label-encoded by 02_preprocess.py using a
# fixed order: Clear=0, Fog=1, Rain=2, Snow=3 (alphabetical, from LabelEncoder
# fit on the full category set) -- this exact mapping must be used consistently
# at inference time too (see backend/app/routers/prediction.py).
PRODUCTION_FEATURES = [
    "Vehicle_Count",
    "Traffic_Speed_kmh",
    "Road_Occupancy_%",
    "Accident_Report",
    "Weather_Condition",
    "hour",
    "day_of_week",
    "is_weekend",
    "is_rush_hour",
]


def main():
    df = pd.read_csv(PROCESSED_DATA_PATH)

    X = df[PRODUCTION_FEATURES]
    y = df[TARGET_COLUMN]

    target_encoder = LabelEncoder()
    y_encoded = target_encoder.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )

    model = RandomForestClassifier(
        n_estimators=200, max_depth=12, random_state=42, class_weight="balanced"
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print(f"Production model accuracy: {accuracy_score(y_test, y_pred):.3f}")
    print(classification_report(y_test, y_pred, target_names=target_encoder.classes_))

    importances = pd.Series(model.feature_importances_, index=PRODUCTION_FEATURES)
    print("\nFeature importances:")
    print(importances.sort_values(ascending=False))

    joblib.dump(model, MODEL_OUTPUT_PATH)
    joblib.dump(target_encoder, TARGET_ENCODER_PATH)
    print(f"\nSaved production model to {MODEL_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
