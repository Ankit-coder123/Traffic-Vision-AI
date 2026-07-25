# TrafficVision AI — Congestion Prediction Model (Week 3&4)

## Dataset

**Source:** [Smart Mobility Traffic Dataset](https://www.kaggle.com/datasets/ziya07/smart-mobility-traffic-dataset) (Kaggle, ziya07)

5,000 records with vehicle counts, speed, road occupancy, traffic light state, weather, accident reports, sentiment, ride-sharing demand, parking availability, emissions, and energy consumption — labeled with a 3-class `Traffic_Condition` target (Low / Medium / High).

This dataset was chosen over the project's own simulator output because it includes external/contextual features (weather, accidents, sentiment) that the simulator doesn't generate, giving the model a richer feature set to learn from.

## Pipeline

Run in order:

```bash
pip install -r requirements.txt

python 01_explore_data.py      # inspect raw structure, confirm column names
python 02_preprocess.py        # clean, engineer time features, encode categoricals
python 03_train_model.py       # train RandomForestClassifier, evaluate, save model
```

Place the downloaded CSV at `data/smart_mobility_traffic.csv` before running.

## Results

- **Accuracy: 99.8%** on a held-out 20% test split
- Top predictive features: `Vehicle_Count`, `Road_Occupancy_%`, `Traffic_Speed_kmh` (combined ~83% of feature importance)

### Important honesty note on the accuracy number

This accuracy is unusually high for a real-world traffic prediction task, and that's worth acknowledging directly rather than presenting at face value. The feature importance breakdown suggests the dataset's `Traffic_Condition` label was likely generated as a near-deterministic function of vehicle count, occupancy, and speed — i.e., the dataset appears synthetically labeled by a rule rather than sourced from messy real-world observations. In a genuinely noisy real-world dataset, congestion depends on many weakly-correlated factors, and accuracy in the 75–90% range would be more typical and more trustworthy.

**How to present this well:** frame the high accuracy as a successful *proof that the modeling pipeline works correctly end-to-end* — data loading, feature engineering, training, evaluation — while being upfront that validating against real-world or noisier data (or your own simulator's longer-running historical data) is the natural next step to get a more realistic accuracy figure.

## Model artifacts

- `models/congestion_model_production.joblib` — trained RandomForestClassifier (used by the live backend)
- `models/target_encoder_production.joblib` — label encoder for the 3-class target
- `models/weather_condition_encoder.joblib` — label encoder for weather categories (Clear/Fog/Rain/Snow)

### Note on the weather feature

Weather was added to the production feature set on request. The EDA (see `eda/EDA_SUMMARY.md`) found weather has near-zero correlation with congestion in this dataset, and retraining confirmed it: weather contributes only ~0.3% feature importance, and accuracy is unchanged with or without it. It's included for completeness and because it's operationally realistic (an operator can select current conditions, or it could later be pulled from a weather API) — but it's honest to note in a presentation that this particular dataset doesn't show weather meaningfully affecting congestion, likely because the dataset's `Traffic_Condition` label was synthetically generated primarily from vehicle count, occupancy, and speed.

## Next steps (Week 3&4 continued)

- Expose this model through a new FastAPI endpoint (`POST /predict/congestion`) so the frontend can request predictions
- Compare against a second dataset (e.g., your own simulator's accumulated historical data, or the UCI Metro Interstate Traffic dataset) to validate whether performance holds up on less "clean" data
- Add a simple feature-importance chart to the dashboard as a model-explainability touch
