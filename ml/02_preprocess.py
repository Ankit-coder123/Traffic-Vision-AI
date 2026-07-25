"""
Step 2: Clean and preprocess the raw Smart Mobility Traffic dataset for model
training.

Dataset: kaggle.com/datasets/ziya07/smart-mobility-traffic-dataset
Confirmed columns (5000 rows, 15 columns):
    Timestamp, Latitude, Longitude, Vehicle_Count, Traffic_Speed_kmh,
    Road_Occupancy_%, Traffic_Light_State, Weather_Condition,
    Accident_Report, Sentiment_Score, Ride_Sharing_Demand,
    Parking_Availability, Emission_Levels_g_km, Energy_Consumption_L_h,
    Traffic_Condition (target: Low / Medium / High)

Usage:
    python 02_preprocess.py
"""

import joblib
import pandas as pd
from sklearn.preprocessing import LabelEncoder

RAW_DATA_PATH = "data/smart_mobility_traffic.csv"
PROCESSED_DATA_PATH = "data/processed_traffic_data.csv"

TARGET_COLUMN = "Traffic_Condition"

# Map the dataset's 3-class labels onto your PostgreSQL schema's 4-value
# enum (low/medium/high/severe). The dataset has no "severe" class, so we
# keep a 3-way mapping here -- worth mentioning as a known limitation.
CONGESTION_LABEL_MAP = {
    "Low": "low",
    "Medium": "medium",
    "High": "high",
}

CATEGORICAL_FEATURES = ["Traffic_Light_State", "Weather_Condition"]


def load_data():
    return pd.read_csv(RAW_DATA_PATH)


def engineer_time_features(df):
    """Extract hour-of-day, day-of-week, weekend, and rush-hour flags --
    typically the strongest predictors for traffic congestion."""
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df["hour"] = df["Timestamp"].dt.hour
    df["day_of_week"] = df["Timestamp"].dt.dayofweek  # 0=Monday
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["is_rush_hour"] = df["hour"].isin([7, 8, 9, 17, 18, 19, 20]).astype(int)
    return df


def clean_missing_values(df):
    numeric_cols = df.select_dtypes(include=["float64", "int64"]).columns
    for col in numeric_cols:
        if df[col].isnull().any():
            df[col] = df[col].fillna(df[col].median())

    categorical_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in categorical_cols:
        if df[col].isnull().any():
            df[col] = df[col].fillna(df[col].mode()[0])

    return df


def encode_categoricals(df):
    """Label-encode categorical feature columns (not the target -- that's
    handled separately in training so we can map back to human-readable
    labels for evaluation)."""
    encoders = {}
    for col in CATEGORICAL_FEATURES:
        if col in df.columns:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            encoders[col] = le
    return df, encoders


def main():
    df = load_data()
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")

    df = engineer_time_features(df)
    df = clean_missing_values(df)
    df, encoders = encode_categoricals(df)
    for name, encoder in encoders.items():
        joblib.dump(encoder, f"models/{name.lower()}_encoder.joblib")
        print(f"Saved {name} encoder -> classes: {list(encoder.classes_)}")

    df[TARGET_COLUMN] = df[TARGET_COLUMN].map(CONGESTION_LABEL_MAP).fillna(
        df[TARGET_COLUMN]
    )

    # Drop raw timestamp and lat/lon -- lat/lon in this dataset are
    # essentially noise (single-city bounding box, not distinct zones),
    # and the timestamp is already decomposed into hour/day/weekend/rush.
    df = df.drop(columns=["Timestamp", "Latitude", "Longitude"])

    df.to_csv(PROCESSED_DATA_PATH, index=False)
    print(f"Saved cleaned data to {PROCESSED_DATA_PATH}")
    print(f"Final shape: {df.shape}")
    print(f"Final columns: {list(df.columns)}")


if __name__ == "__main__":
    main()
