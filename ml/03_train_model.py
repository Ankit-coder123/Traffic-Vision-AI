"""
Step 3: Train a congestion prediction model on the cleaned dataset.

Usage:
    python 03_train_model.py
"""

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

PROCESSED_DATA_PATH = "data/processed_traffic_data.csv"
MODEL_OUTPUT_PATH = "models/congestion_model.joblib"
TARGET_ENCODER_PATH = "models/target_encoder.joblib"

TARGET_COLUMN = "Traffic_Condition"

# Columns to exclude from features (identifiers, raw timestamps, target)
DROP_COLUMNS = ["timestamp", TARGET_COLUMN]


def load_processed_data():
    return pd.read_csv(PROCESSED_DATA_PATH)


def prepare_features_and_target(df):
    feature_cols = [c for c in df.columns if c not in DROP_COLUMNS]
    X = df[feature_cols]
    y = df[TARGET_COLUMN]

    # Keep only numeric feature columns (any leftover unencoded text columns
    # would break the model -- this is a safety net, not a substitute for
    # proper encoding in the preprocessing step)
    X = X.select_dtypes(include=["number"])

    return X, y, list(X.columns)


def main():
    df = load_processed_data()
    X, y, feature_names = prepare_features_and_target(df)

    print(f"Training on {len(feature_names)} features: {feature_names}")
    print(f"Target distribution:\n{y.value_counts()}")

    target_encoder = LabelEncoder()
    y_encoded = target_encoder.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        random_state=42,
        class_weight="balanced",  # helps if congestion levels are imbalanced
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    print("\n" + "=" * 60)
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.3f}")
    print("=" * 60)
    print("\nClassification Report:")
    print(
        classification_report(
            y_test, y_pred, target_names=target_encoder.classes_
        )
    )
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    # Feature importance -- useful talking point for a presentation
    importances = pd.Series(model.feature_importances_, index=feature_names)
    print("\nTop feature importances:")
    print(importances.sort_values(ascending=False).head(10))

    joblib.dump(model, MODEL_OUTPUT_PATH)
    joblib.dump(target_encoder, TARGET_ENCODER_PATH)
    print(f"\nSaved model to {MODEL_OUTPUT_PATH}")
    print(f"Saved target encoder to {TARGET_ENCODER_PATH}")


if __name__ == "__main__":
    main()
