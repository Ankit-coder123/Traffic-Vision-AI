import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
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

export default function Prediction() {
  const navigate = useNavigate();
  const location = useLocation();
  const [zones, setZones] = useState([]);
  const now = new Date();
  const [form, setForm] = useState({
    origin_zone_id: location.state?.originId ? String(location.state.originId) : "",
    destination_zone_id: location.state?.destinationId ? String(location.state.destinationId) : "",
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
    const isStringField =
      field === "origin_zone_id" || field === "destination_zone_id" || field === "weather_condition";
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!form.origin_zone_id || !form.destination_zone_id) {
      setError("Select both an origin and a destination zone.");
      return;
    }
    if (form.origin_zone_id === form.destination_zone_id) {
      setError("Origin and destination must be different zones.");
      return;
    }

    setLoading(true);
    setResult(null);
    try {
      const payload = {
        origin_zone_id: Number(form.origin_zone_id),
        destination_zone_id: Number(form.destination_zone_id),
        vehicle_count: form.vehicle_count,
        avg_speed_kmph: form.avg_speed_kmph,
        road_occupancy_pct: form.road_occupancy_pct,
        weather_condition: form.weather_condition,
        hour: form.hour,
        is_weekend: form.is_weekend,
      };

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

  const handleViewOptimizedRoute = () => {
    navigate("/routes", {
      state: {
        originId: form.origin_zone_id,
        destinationId: form.destination_zone_id,
        autoSearch: true,
        predictedCongestion: result?.predicted_congestion,
      },
    });
  };

  const zoneName = (id) => zones.find((z) => String(z.id) === String(id))?.name || "";

  const handleDownloadPdf = () => {
    const doc = new jsPDF();

    doc.setFontSize(16);
    doc.text("TrafficVision AI — Congestion Prediction Report", 14, 18);
    doc.setFontSize(10);
    doc.setTextColor(100);
    doc.text(`Bangalore · Generated ${new Date().toLocaleString()}`, 14, 25);

    let startY = 32;

    // If there's a currently-viewed prediction result, lead with it as a summary block
    if (result) {
      doc.setFontSize(12);
      doc.setTextColor(0);
      doc.text("Latest Prediction", 14, startY + 6);

      autoTable(doc, {
        startY: startY + 10,
        head: [["Route", "Predicted Congestion", "Confidence", "Vehicles", "Speed", "Occupancy", "Weather", "Time"]],
        body: [[
          `${zoneName(form.origin_zone_id) || "—"} -> ${zoneName(form.destination_zone_id) || "—"}`,
          result.predicted_congestion.toUpperCase(),
          `${(result.confidence * 100).toFixed(1)}%`,
          form.vehicle_count,
          `${form.avg_speed_kmph} km/h`,
          `${form.road_occupancy_pct}%`,
          form.weather_condition,
          `${formatHour(form.hour)} (${form.is_weekend ? "Weekend" : "Weekday"})`,
        ]],
        theme: "grid",
        headStyles: { fillColor: [34, 211, 238] },
        styles: { fontSize: 8 },
      });

      startY = doc.lastAutoTable.finalY + 12;
    }

    doc.setFontSize(12);
    doc.setTextColor(0);
    doc.text("Recent Prediction History", 14, startY);

    if (reports.length === 0) {
      doc.setFontSize(10);
      doc.setTextColor(120);
      doc.text("No predictions logged yet.", 14, startY + 8);
    } else {
      autoTable(doc, {
        startY: startY + 4,
        head: [["Time", "Route", "Vehicles", "Speed", "Occupancy", "Weather", "Prediction", "Confidence"]],
        body: reports.map((r) => [
          new Date(r.created_at).toLocaleString(),
          r.origin_zone_id && r.destination_zone_id
            ? `${zoneName(r.origin_zone_id) || "?"} -> ${zoneName(r.destination_zone_id) || "?"}`
            : "—",
          r.vehicle_count,
          `${r.avg_speed_kmph} km/h`,
          `${r.road_occupancy_pct}%`,
          r.weather_condition,
          r.predicted_congestion.toUpperCase(),
          `${(r.confidence * 100).toFixed(1)}%`,
        ]),
        theme: "striped",
        headStyles: { fillColor: [34, 211, 238] },
        styles: { fontSize: 8 },
      });
    }

    const filename = `trafficvision-prediction-report-${new Date().toISOString().slice(0, 10)}.pdf`;
    doc.save(filename);
  };

  return (
    <div className="min-h-screen bg-console-bg">
      <NavBar />
      <div className="max-w-6xl mx-auto px-6 py-8 animate-fade-in">
      <div className="mb-6">
        <h2 className="font-display font-bold text-xl text-console-text">
          Congestion Prediction
        </h2>
        <p className="text-console-muted text-sm font-mono mt-1">
          Predict congestion for a specific route, then jump straight to optimized alternatives
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input form */}
        <form
          onSubmit={handleSubmit}
          className="bg-console-panel border border-console-border rounded-lg p-6"
        >
          <h3 className="font-display font-semibold text-console-text text-sm mb-4 uppercase tracking-wide">
            Route
          </h3>

          <div className="grid grid-cols-2 gap-3 mb-5">
            <label className="block">
              <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
                From
              </span>
              <select
                value={form.origin_zone_id}
                onChange={handleChange("origin_zone_id")}
                className="w-full bg-console-bg border border-console-border rounded px-3 py-2.5 text-console-text focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent font-body text-sm"
              >
                <option value="">Select origin</option>
                {zones.map((z) => (
                  <option key={z.id} value={z.id}>
                    {z.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
                To
              </span>
              <select
                value={form.destination_zone_id}
                onChange={handleChange("destination_zone_id")}
                className="w-full bg-console-bg border border-console-border rounded px-3 py-2.5 text-console-text focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent font-body text-sm"
              >
                <option value="">Select destination</option>
                {zones.map((z) => (
                  <option key={z.id} value={z.id}>
                    {z.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <h3 className="font-display font-semibold text-console-text text-sm mb-4 uppercase tracking-wide">
            Traffic Conditions
          </h3>

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
            className="w-full bg-accent text-console-bg font-display font-semibold rounded py-2.5 text-sm tracking-wide hover:bg-accent/90 active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100 transition"
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
              Select a route and traffic conditions, then click Predict to see the model's output.
            </div>
          )}

          {result && (
            <div>
              <div className="text-console-text text-sm font-body mb-3 pb-3 border-b border-console-border">
                <span className="font-medium">{zoneName(form.origin_zone_id)}</span>
                <span className="text-console-muted mx-2">&rarr;</span>
                <span className="font-medium">{zoneName(form.destination_zone_id)}</span>
              </div>

              {resultContext && (
                <div className="text-console-muted text-xs font-mono mb-3">
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

              <div className="space-y-3 mb-5">
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

              <button
                type="button"
                onClick={handleViewOptimizedRoute}
                className="w-full bg-accent/10 border border-accent/40 text-accent font-display font-semibold rounded py-2.5 text-sm tracking-wide hover:bg-accent/20 transition-colors flex items-center justify-center gap-2"
              >
                View Optimized Route
                <span aria-hidden="true">&rarr;</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Recent reports */}
      <div className="mt-6 bg-console-panel border border-console-border rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-display font-semibold text-console-text text-sm uppercase tracking-wide">
            Recent Prediction Reports
          </h3>
          <button
            type="button"
            onClick={handleDownloadPdf}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-accent/40 text-accent text-xs font-mono uppercase tracking-wide hover:bg-accent/10 transition-colors"
          >
            <span aria-hidden="true">&#8681;</span>
            Download PDF
          </button>
        </div>

        {reports.length === 0 ? (
          <p className="text-console-muted text-sm font-body">No predictions logged yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-console-muted text-xs font-mono uppercase tracking-wide border-b border-console-border">
                  <th className="pb-2 pr-4">Time</th>
                  <th className="pb-2 pr-4">Route</th>
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
                    <td className="py-2 pr-4 text-console-muted">
                      {r.origin_zone_id && r.destination_zone_id
                        ? `${zoneName(r.origin_zone_id) || "?"} → ${zoneName(r.destination_zone_id) || "?"}`
                        : "—"}
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
