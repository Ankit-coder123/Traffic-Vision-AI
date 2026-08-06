from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas, security, traffic_model
from app.database import get_db

router = APIRouter(prefix="/predict", tags=["Congestion Prediction"])


def _resolve_time_features(payload: schemas.CongestionPredictionRequest):
    """hour/is_weekend default to 'right now' unless the caller pins them
    (useful for 'what would congestion look like at 6pm' what-if queries)."""
    now = datetime.utcnow()
    hour = payload.hour if payload.hour is not None else now.hour
    is_weekend = (
        payload.is_weekend if payload.is_weekend is not None else now.weekday() >= 5
    )
    return hour, is_weekend


@router.post("/congestion", response_model=schemas.CongestionPredictionResponse)
def predict_congestion(
    payload: schemas.CongestionPredictionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Predicts congestion level (low/medium/high) from live traffic metrics
    using the RandomForest model trained in ml/04_train_production_model.py.
    Every prediction is also logged to traffic_predictions for reporting.
    """
    hour, is_weekend = _resolve_time_features(payload)

    predicted_label, confidence, prob_dict = traffic_model.predict_congestion(
        vehicle_count=payload.vehicle_count,
        avg_speed_kmph=payload.avg_speed_kmph,
        road_occupancy_pct=payload.road_occupancy_pct,
        accident_report=0,  # not yet tracked live; defaults to "no accident"
        weather_condition=payload.weather_condition,
        hour=hour,
        is_weekend=is_weekend,
    )

    # Log the prediction for the "traffic prediction reports" requirement
    record = models.TrafficPrediction(
        origin_zone_id=payload.origin_zone_id,
        destination_zone_id=payload.destination_zone_id,
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
        origin_zone_id=payload.origin_zone_id,
        destination_zone_id=payload.destination_zone_id,
    )


@router.get("/reports", response_model=list[schemas.TrafficPredictionOut])
def get_prediction_reports(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Returns the most recent prediction reports -- satisfies the 'generate
    traffic prediction reports' requirement from the Week 3&4 milestone."""
    return (
        db.query(models.TrafficPrediction)
        .order_by(models.TrafficPrediction.created_at.desc())
        .limit(limit)
        .all()
    )
