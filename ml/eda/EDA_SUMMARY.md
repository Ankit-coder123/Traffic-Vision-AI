# EDA — Smart Mobility Traffic Dataset

## Dataset shape
5,000 rows × 15 columns. No missing values. Timestamps span a continuous period at regular intervals.

## Class distribution
`Traffic_Condition` is reasonably balanced across Low / Medium / High (see `01_class_distribution.png`) — no major class imbalance to correct for.

## Correlation with target

| Feature | Correlation with congestion |
|---|---|
| `Vehicle_Count` | **+0.49** (strongest) |
| `Road_Occupancy_%` | +0.34 |
| `Accident_Report` | +0.23 |
| `Traffic_Speed_kmh` | **-0.29** (higher speed → less congestion, as expected) |
| Emissions, sentiment, ride-sharing demand, parking, energy use, lat/lon | all under ±0.03 — essentially no linear relationship |

## Key finding: this dataset appears rule-generated, not observational

Three pieces of evidence, all pointing the same direction:

1. **Boxplots by class show near-total separation** (`03_vehicle_count_by_class.png`, `04_speed_by_class.png`) — Low/Medium/High barely overlap in vehicle count or speed. Real-world traffic data is messier than this; classes usually overlap substantially.
2. **No hourly rush-hour pattern** (`05_hourly_pattern.png`) — congestion counts are flat and noisy across all 24 hours, with no morning/evening peaks. Real traffic data almost always shows a clear rush-hour signature.
3. **8 of 11 numeric features have near-zero correlation with the target** — weather, sentiment, ride-sharing demand, parking, emissions, and energy consumption appear to be randomly generated, unrelated to the labeled congestion level.

**Practical takeaway**: `Vehicle_Count`, `Road_Occupancy_%`, and `Traffic_Speed_kmh` are the only features doing real predictive work — which lines up exactly with the 83% combined feature importance the trained model found. The other 8 columns (weather, sentiment, ride-sharing, parking, emissions, energy, lat/lon) can reasonably be treated as noise for this particular dataset, though they'd likely matter in real-world data.

## Charts

| File | Shows |
|---|---|
| `01_class_distribution.png` | Class balance across Low/Medium/High |
| `02_correlation_heatmap.png` | Full feature correlation matrix |
| `03_vehicle_count_by_class.png` | Vehicle count distribution per class |
| `04_speed_by_class.png` | Speed distribution per class |
| `05_hourly_pattern.png` | Congestion counts by hour of day |
