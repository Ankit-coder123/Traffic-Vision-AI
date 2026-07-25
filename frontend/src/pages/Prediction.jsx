import { useEffect, useState } from "react";
import { predictionApi, trafficApi } from "../api/client";
import NavBar from "../components/NavBar";

const LEVEL_STYLES = {
  low: { text: "text-signal-low", bg: "bg-signal-low", badge: "bg-signal-low/10 text-signal-low border-signal-low/30", icon: "🟢" },
  medium: { text: "text-signal-medium", bg: "bg-signal-medium", badge: "bg-signal-medium/10 text-signal-medium border-signal-medium/30", icon: "🟡" },
  high: { text: "text-signal-high", bg: "bg-signal-high", badge: "bg-signal-high/10 text-signal-high border-signal-high/30", icon: "🔴" },
};

const WEATHER_OPTIONS = ["Clear", "Fog", "Rain", "Snow"];

function formatHour(h) {
  const period = h < 12 ? "AM" : "PM";
  const displayHour = h % 12 === 0 ? 12 : h % 12;
  return `${displayHour}:00 ${period}`;
}

const HOUR_OPTIONS = Array.from({ length: 24 }, (_, h) => h);

const SCENARIO_PRESETS = [
  { label: "Free Flow", vehicle_count: 40, avg_speed_kmph: 70, road_occupancy_pct: 15, weather_condition: "Clear", hour: 2, is_weekend: false },
  { label: "Moderate", vehicle_count: 150, avg_speed_kmph: 35, road_occupancy_pct: 50, weather_condition: "Clear", hour: 13, is_weekend: false },
  { label: "Rush Hour", vehicle_count: 260, avg_speed_kmph: 15, road_occupancy_pct: 85, weather_condition: "Clear", hour: 18, is_weekend: false },
  { label: "Storm Gridlock", vehicle_count: 280, avg_speed_kmph: 8, road_occupancy_pct: 95, weather_condition: "Rain", hour: 8, is_weekend: false },
];

export default function Prediction() {
  const [zones, setZones] = useState([]);
  const now = new Date();
  const [form, setForm] = useState({
    zone_id: "",
    vehicle_count: 150,
    avg_speed_kmph: 35,
    road_occupancy_pct: 50,
    weather_condition: "Clear",
    hour: now.getHours(),
    is_weekend: now.getDay() === 0 || now.getDay() === 6,
  });
  const [result, setResult] = useState(null);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [resultContext, setResultContext] = useState(null);

  useEffect(() => {
    trafficApi.getZones().then((res) => setZones(res.data)).catch(() => {});
    loadReports();
  }, []);

  const loadReports = () => {
    predictionApi
      .getReports(10)
      .then((res) => setReports(res.data))
      .catch(() => {});
  };

  const handleChange = (field) => (e) => {
    const isStringField = field === "zone_id" || field === "weather_condition";
    const value = isStringField ? e.target.value : Number(e.target.value);
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const toggleDayType = (isWeekend) => {
    setForm((prev) => ({ ...prev, is_weekend: isWeekend }));
  };

  const useCurrentTime = () => {
    const n = new Date();
    setForm((prev) => ({
      ...prev,
      hour: n.getHours(),
      is_weekend: n.getDay() === 0 || n.getDay() === 6,
    }));
  };

  const applyPreset = (preset) => {
    setForm((prev) => ({
      ...prev,
      vehicle_count: preset.vehicle_count,
      avg_speed_kmph: preset.avg_speed_kmph,
      road_occupancy_pct: preset.road_occupancy_pct,
      weather_condition: preset.weather_condition,
      hour: preset.hour,
      is_weekend: preset.is_weekend,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    setResult(null);
    try {
      const payload = {
        vehicle_count: form.vehicle_count,
        avg_speed_kmph: form.avg_speed_kmph,
        road_occupancy_pct: form.road_occupancy_pct,
        weather_condition: form.weather_condition,
        hour: form.hour,
        is_weekend: form.is_weekend,
      };
      if (form.zone_id) payload.zone_id = Number(form.zone_id);

      const res = await predictionApi.predictCongestion(payload);
      setResult(res.data);
      setResultContext({ hour: form.hour, is_weekend: form.is_weekend });
      loadReports();
    } catch (err) {
      setError(
        err.response?.data?.detail
          ? JSON.stringify(err.response.data.detail)
          : "Prediction failed. Check that the backend is running."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-console-bg">
      <NavBar />
      <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="mb-6">
        <h2 className="font-display font-bold text-xl text-console-text">
          Congestion Prediction
        </h2>
        <p className="text-console-muted text-sm font-mono mt-1">
          RandomForest model &middot; trained on vehicle count, speed, occupancy &amp; time features
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input form */}
        <form
          onSubmit={handleSubmit}
          className="bg-console-panel border border-console-border rounded-lg p-6"
        >
          <h3 className="font-display font-semibold text-console-text text-sm mb-4 uppercase tracking-wide">
            Traffic Conditions
          </h3>

          <div className="mb-5">
            <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-2">
              Quick Scenarios
            </span>
            <div className="grid grid-cols-2 gap-2">
              {SCENARIO_PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  onClick={() => applyPreset(preset)}
                  className="px-3 py-2 rounded border border-console-border bg-console-bg hover:border-accent/50 hover:bg-accent/5 text-console-text text-xs font-mono uppercase tracking-wide transition-colors"
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          <label className="block mb-4">
            <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
              Zone (optional)
            </span>
            <select
              value={form.zone_id}
              onChange={handleChange("zone_id")}
              className="w-full bg-console-bg border border-console-border rounded px-3 py-2.5 text-console-text focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent font-body text-sm"
            >
              <option value="">— Not tied to a zone —</option>
              {zones.map((z) => (
                <option key={z.id} value={z.id}>
                  {z.name}
                </option>
              ))}
            </select>
          </label>

          <label className="block mb-4">
            <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
              Weather
            </span>
            <select
              value={form.weather_condition}
              onChange={handleChange("weather_condition")}
              className="w-full bg-console-bg border border-console-border rounded px-3 py-2.5 text-console-text focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent font-body text-sm"
            >
              {WEATHER_OPTIONS.map((w) => (
                <option key={w} value={w}>
                  {w}
                </option>
              ))}
            </select>
          </label>

          <div className="mb-4">
            <div className="flex items-center justify-between mb-1.5">
              <span className="block text-xs font-mono text-console-muted uppercase tracking-wide">
                Time of Day
              </span>
              <button
                type="button"
                onClick={useCurrentTime}
                className="text-[10px] font-mono text-accent hover:underline uppercase tracking-wide"
              >
                Use now
              </button>
            </div>
            <select
              value={form.hour}
              onChange={handleChange("hour")}
              className="w-full bg-console-bg border border-console-border rounded px-3 py-2.5 text-console-text focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent font-body text-sm mb-2"
            >
              {HOUR_OPTIONS.map((h) => (
                <option key={h} value={h}>
                  {formatHour(h)}
                  {h >= 7 && h <= 9 ? "  (morning rush)" : h >= 17 && h <= 20 ? "  (evening rush)" : ""}
                </option>
              ))}
            </select>

            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => toggleDayType(false)}
                className={`px-3 py-2 rounded border text-xs font-mono uppercase tracking-wide transition-colors ${
                  !form.is_weekend
                    ? "border-accent bg-accent/10 text-accent"
                    : "border-console-border text-console-muted hover:text-console-text"
                }`}
              >
                Weekday
              </button>
              <button
                type="button"
                onClick={() => toggleDayType(true)}
                className={`px-3 py-2 rounded border text-xs font-mono uppercase tracking-wide transition-colors ${
                  form.is_weekend
                    ? "border-accent bg-accent/10 text-accent"
                    : "border-console-border text-console-muted hover:text-console-text"
                }`}
              >
                Weekend
              </button>
            </div>
          </div>

          <label className="block mb-4">
            <span className="flex justify-between text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
              <span>Vehicle Count</span>
              <span className="text-accent">{form.vehicle_count}</span>
            </span>
            <input
              type="range"
              min="0"
              max="300"
              value={form.vehicle_count}
              onChange={handleChange("vehicle_count")}
              className="w-full accent-accent"
            />
          </label>

          <label className="block mb-4">
            <span className="flex justify-between text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
              <span>Avg Speed (km/h)</span>
              <span className="text-accent">{form.avg_speed_kmph}</span>
            </span>
            <input
              type="range"
              min="0"
              max="100"
              value={form.avg_speed_kmph}
              onChange={handleChange("avg_speed_kmph")}
              className="w-full accent-accent"
            />
          </label>

          <label className="block mb-6">
            <span className="flex justify-between text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
              <span>Road Occupancy (%)</span>
              <span className="text-accent">{form.road_occupancy_pct}</span>
            </span>
            <input
              type="range"
              min="0"
              max="100"
              value={form.road_occupancy_pct}
              onChange={handleChange("road_occupancy_pct")}
              className="w-full accent-accent"
            />
          </label>

          {error && (
            <div className="mb-4 px-3 py-2 rounded bg-signal-severe/10 border border-signal-severe/30 text-signal-severe text-sm font-body">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-accent text-console-bg font-display font-semibold rounded py-2.5 text-sm tracking-wide hover:bg-accent/90 disabled:opacity-50 transition-colors"
          >
            {loading ? "Predicting..." : "Predict Congestion"}
          </button>
        </form>

        {/* Result panel */}
        <div className="bg-console-panel border border-console-border rounded-lg p-6">
          <h3 className="font-display font-semibold text-console-text text-sm mb-4 uppercase tracking-wide">
            Prediction Result
          </h3>

          {!result && (
            <div className="text-console-muted text-sm font-body py-12 text-center">
              Fill in traffic conditions and click Predict to see the model's output.
            </div>
          )}

          {result && (
            <div>
              {resultContext && (
                <div className="text-console-muted text-xs font-mono mb-3 pb-3 border-b border-console-border">
                  Forecast for {formatHour(resultContext.hour)} &middot;{" "}
                  {resultContext.is_weekend ? "Weekend" : "Weekday"}
                </div>
              )}

              <div
                className={`inline-flex items-center gap-2 px-3 py-1.5 rounded text-sm font-mono uppercase tracking-wide mb-4 border ${
                  LEVEL_STYLES[result.predicted_congestion]?.badge
                }`}
              >
                <span>{LEVEL_STYLES[result.predicted_congestion]?.icon}</span>
                {result.predicted_congestion} congestion
              </div>

              <div className="text-console-muted text-xs font-mono mb-4">
                Confidence: {(result.confidence * 100).toFixed(1)}%
              </div>

              <div className="space-y-3">
                {Object.entries(result.probabilities)
                  .sort((a, b) => b[1] - a[1])
                  .map(([level, prob]) => (
                    <div key={level}>
                      <div className="flex justify-between text-xs font-mono text-console-muted mb-1">
                        <span className="uppercase">{level}</span>
                        <span>{(prob * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full h-2 bg-console-bg rounded-full overflow-hidden">
                        <div
                          className={`h-full ${LEVEL_STYLES[level]?.bg} rounded-full transition-all`}
                          style={{ width: `${prob * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Recent reports */}
      <div className="mt-6 bg-console-panel border border-console-border rounded-lg p-6">
        <h3 className="font-display font-semibold text-console-text text-sm mb-4 uppercase tracking-wide">
          Recent Prediction Reports
        </h3>

        {reports.length === 0 ? (
          <p className="text-console-muted text-sm font-body">No predictions logged yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-console-muted text-xs font-mono uppercase tracking-wide border-b border-console-border">
                  <th className="pb-2 pr-4">Time</th>
                  <th className="pb-2 pr-4">Vehicles</th>
                  <th className="pb-2 pr-4">Speed</th>
                  <th className="pb-2 pr-4">Occupancy</th>
                  <th className="pb-2 pr-4">Prediction</th>
                  <th className="pb-2">Confidence</th>
                </tr>
              </thead>
              <tbody className="font-mono text-console-text">
                {reports.map((r) => (
                  <tr key={r.id} className="border-b border-console-border/50">
                    <td className="py-2 pr-4 text-console-muted">
                      {new Date(r.created_at).toLocaleTimeString()}
                    </td>
                    <td className="py-2 pr-4">{r.vehicle_count}</td>
                    <td className="py-2 pr-4">{r.avg_speed_kmph} km/h</td>
                    <td className="py-2 pr-4">{r.road_occupancy_pct}%</td>
                    <td className="py-2 pr-4">
                      <span className={LEVEL_STYLES[r.predicted_congestion]?.text}>
                        {r.predicted_congestion}
                      </span>
                    </td>
                    <td className="py-2">{(r.confidence * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      </div>
    </div>
  );
}
