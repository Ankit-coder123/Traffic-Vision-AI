"""
Shared wrapper around the trained RandomForestClassifier (see
ml/04_train_production_model.py). Both the manual /predict/congestion
endpoint and the analytics recommendations engine call into this module,
so there's one place that owns feature encoding and model loading instead
of two copies drifting apart.
"""

from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd

MODEL_DIR = Path(__file__).parent
_model = joblib.load(MODEL_DIR / "congestion_model.joblib")
_target_encoder = joblib.load(MODEL_DIR / "target_encoder.joblib")

FEATURE_ORDER = [
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

# Fixed encoding matching the LabelEncoder order used in ml/02_preprocess.py
# (alphabetical: Clear=0, Fog=1, Rain=2, Snow=3). Must stay in sync with
# training -- if the training data's category set ever changes, this map
# needs updating to match.
WEATHER_ENCODING = {"Clear": 0, "Fog": 1, "Rain": 2, "Snow": 3}

# Same per-road-type capacity assumptions as backend/simulator.py, used to
# turn a raw vehicle count into the Road_Occupancy_% feature the model was
# trained on when we only have live vehicle_count/avg_speed readings (e.g.
# from TrafficData) rather than a full prediction request payload.
ROAD_TYPE_CAPACITY = {"highway": 300, "arterial": 180, "local": 90}


def estimate_road_occupancy_pct(vehicle_count: float, road_type: str) -> float:
    capacity = ROAD_TYPE_CAPACITY.get(road_type, 150)
    return round(min(vehicle_count / capacity, 1.5) * 100, 1)


def build_feature_row(
    vehicle_count: float,
    avg_speed_kmph: float,
    road_occupancy_pct: float,
    accident_report: int = 0,
    weather_condition: str = "Clear",
    hour: int = None,
    is_weekend: bool = None,
) -> pd.DataFrame:
    now = datetime.utcnow()
    hour = hour if hour is not None else now.hour
    day_of_week = now.weekday()
    is_weekend = is_weekend if is_weekend is not None else day_of_week >= 5
    is_rush_hour = hour in (7, 8, 9, 17, 18, 19, 20)

    row = {
        "Vehicle_Count": vehicle_count,
        "Traffic_Speed_kmh": avg_speed_kmph,
        "Road_Occupancy_%": road_occupancy_pct,
        "Accident_Report": accident_report,
        "Weather_Condition": WEATHER_ENCODING.get(weather_condition, WEATHER_ENCODING["Clear"]),
        "hour": hour,
        "day_of_week": day_of_week,
        "is_weekend": int(is_weekend),
        "is_rush_hour": int(is_rush_hour),
    }
    return pd.DataFrame([row], columns=FEATURE_ORDER)


def predict_congestion(
    vehicle_count: float,
    avg_speed_kmph: float,
    road_occupancy_pct: float,
    accident_report: int = 0,
    weather_condition: str = "Clear",
    hour: int = None,
    is_weekend: bool = None,
):
    """Returns (predicted_label, confidence, probabilities_dict)."""
    features = build_feature_row(
        vehicle_count=vehicle_count,
        avg_speed_kmph=avg_speed_kmph,
        road_occupancy_pct=road_occupancy_pct,
        accident_report=accident_report,
        weather_condition=weather_condition,
        hour=hour,
        is_weekend=is_weekend,
    )

    probabilities = _model.predict_proba(features)[0]
    predicted_idx = probabilities.argmax()
    predicted_label = _target_encoder.classes_[predicted_idx]
    confidence = float(probabilities[predicted_idx])
    prob_dict = {cls: float(p) for cls, p in zip(_target_encoder.classes_, probabilities)}

    return predicted_label, confidence, prob_dict
