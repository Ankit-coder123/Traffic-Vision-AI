from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas, auth
from app.database import get_db

router = APIRouter(prefix="/predict", tags=["Congestion Prediction"])

MODEL_DIR = Path(__file__).parent.parent
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


def _build_feature_row(payload: schemas.CongestionPredictionRequest) -> pd.DataFrame:
    now = datetime.utcnow()
    hour = payload.hour if payload.hour is not None else now.hour
    day_of_week = now.weekday()
    is_weekend = (
        payload.is_weekend if payload.is_weekend is not None else day_of_week >= 5
    )
    is_rush_hour = hour in (7, 8, 9, 17, 18, 19, 20)

    row = {
        "Vehicle_Count": payload.vehicle_count,
        "Traffic_Speed_kmh": payload.avg_speed_kmph,
        "Road_Occupancy_%": payload.road_occupancy_pct,
        "Accident_Report": 0,  # not yet tracked live; defaults to "no accident"
        "Weather_Condition": WEATHER_ENCODING.get(payload.weather_condition, WEATHER_ENCODING["Clear"]),
        "hour": hour,
        "day_of_week": day_of_week,
        "is_weekend": int(is_weekend),
        "is_rush_hour": int(is_rush_hour),
    }
    return pd.DataFrame([row], columns=FEATURE_ORDER)


@router.post("/congestion", response_model=schemas.CongestionPredictionResponse)
def predict_congestion(
    payload: schemas.CongestionPredictionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Predicts congestion level (low/medium/high) from live traffic metrics
    using the RandomForest model trained in ml/04_train_production_model.py.
    Every prediction is also logged to traffic_predictions for reporting.
    """
    features = _build_feature_row(payload)

    probabilities = _model.predict_proba(features)[0]
    predicted_idx = probabilities.argmax()
    predicted_label = _target_encoder.classes_[predicted_idx]
    confidence = float(probabilities[predicted_idx])

    prob_dict = {
        cls: float(prob)
        for cls, prob in zip(_target_encoder.classes_, probabilities)
    }

    # Log the prediction for the "traffic prediction reports" requirement
    record = models.TrafficPrediction(
        zone_id=payload.zone_id,
        vehicle_count=payload.vehicle_count,
        avg_speed_kmph=payload.avg_speed_kmph,
        road_occupancy_pct=payload.road_occupancy_pct,
        weather_condition=payload.weather_condition,
        predicted_congestion=predicted_label,
        confidence=confidence,
        predicted_by_user_id=current_user.id,
    )
    db.add(record)
    db.commit()

    return schemas.CongestionPredictionResponse(
        predicted_congestion=predicted_label,
        confidence=confidence,
        probabilities=prob_dict,
    )


@router.get("/reports", response_model=list[schemas.TrafficPredictionOut])
def get_prediction_reports(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Returns the most recent prediction reports -- satisfies the 'generate
    traffic prediction reports' requirement from the Week 3&4 milestone."""
    return (
        db.query(models.TrafficPrediction)
        .order_by(models.TrafficPrediction.created_at.desc())
        .limit(limit)
        .all()
    )
