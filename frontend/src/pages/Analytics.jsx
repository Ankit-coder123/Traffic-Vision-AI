import { useEffect, useState } from "react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  Legend,
} from "recharts";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.heat";
import { analyticsApi, trafficApi } from "../api/client";
import NavBar from "../components/NavBar";

// Maps congestion level to a heat "intensity" weight -- fed into Leaflet.heat
// as the third value per point ([lat, lng, intensity]). Higher intensity
// renders redder/denser on the gradient.
const CONGESTION_INTENSITY = { low: 0.25, medium: 0.5, high: 0.75, severe: 1.0 };

// Leaflet.heat isn't a react-leaflet component -- it operates directly on the
// underlying Leaflet map instance via L.heatLayer(). This wrapper mounts/
// unmounts that layer declaratively whenever `points` changes, using
// react-leaflet's useMap() hook to access the map instance from inside
// <MapContainer>.
function HeatmapLayer({ points }) {
  const map = useMap();

  useEffect(() => {
    if (!points.length) return undefined;

    const heatData = points.map((p) => [
      p.latitude,
      p.longitude,
      CONGESTION_INTENSITY[p.congestion_level] ?? 0.25,
    ]);

    const heatLayer = L.heatLayer(heatData, {
      radius: 40,
      blur: 30,
      maxZoom: 14,
      max: 1.0,
      gradient: {
        0.25: "#34D399", // low - green
        0.5: "#FBBF24",  // medium - amber
        0.75: "#FB923C", // high - orange
        1.0: "#F43F5E",  // severe - red
      },
    });

    heatLayer.addTo(map);
    return () => {
      map.removeLayer(heatLayer);
    };
  }, [points, map]);

  return null;
}

const LEVEL_COLORS = {
  low: "#34D399",
  medium: "#FBBF24",
  high: "#FB923C",
  severe: "#F43F5E",
};

const SEVERITY_STYLES = {
  critical: "border-signal-severe/40 bg-signal-severe/5 text-signal-severe",
  warning: "border-signal-medium/40 bg-signal-medium/5 text-signal-medium",
  info: "border-accent/40 bg-accent/5 text-accent",
};

const TREND_WINDOWS = [
  { label: "24h", hours: 24 },
  { label: "3 Days", hours: 72 },
  { label: "7 Days", hours: 168 },
];

export default function Analytics() {
  const [summary, setSummary] = useState(null);
  const [heatmap, setHeatmap] = useState([]);
  const [zones, setZones] = useState([]);
  const [trends, setTrends] = useState([]);
  const [selectedZoneId, setSelectedZoneId] = useState("");
  const [windowHours, setWindowHours] = useState(24);
  const [recommendations, setRecommendations] = useState([]);
  const [roadPerformance, setRoadPerformance] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    trafficApi.getZones().then((res) => setZones(res.data)).catch(() => {});
    loadAll();
    const interval = setInterval(loadAll, 15000); // refresh every 15s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    loadTrends();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedZoneId, windowHours]);

  const loadAll = () => {
    analyticsApi.getSummary().then((res) => setSummary(res.data)).catch(() => {});
    analyticsApi.getHeatmap().then((res) => setHeatmap(res.data)).catch(() => {});
    analyticsApi.getRecommendations().then((res) => setRecommendations(res.data)).catch(() => {});
    analyticsApi.getRoadPerformance(24).then((res) => setRoadPerformance(res.data)).catch(() => {});
    setLoading(false);
  };

  const loadTrends = () => {
    analyticsApi
      .getTrends(windowHours, selectedZoneId || null)
      .then((res) => setTrends(res.data))
      .catch(() => {});
  };

  // Merge per-zone trend points into a single chart-friendly series when "All zones" is
  // selected (average congestion score across zones per period); otherwise use the single
  // selected zone's points directly.
  const chartData = (() => {
    if (selectedZoneId) {
      const zoneTrend = trends.find((t) => String(t.zone_id) === String(selectedZoneId));
      return zoneTrend?.points || [];
    }
    const byPeriod = {};
    trends.forEach((zoneTrend) => {
      zoneTrend.points.forEach((p) => {
        if (!byPeriod[p.period]) byPeriod[p.period] = { period: p.period, scores: [], speeds: [] };
        byPeriod[p.period].scores.push(p.congestion_score);
        byPeriod[p.period].speeds.push(p.avg_speed_kmph);
      });
    });
    return Object.values(byPeriod)
      .sort((a, b) => a.period.localeCompare(b.period))
      .map((b) => ({
        period: b.period,
        congestion_score: +(b.scores.reduce((a, c) => a + c, 0) / b.scores.length).toFixed(2),
        avg_speed_kmph: +(b.speeds.reduce((a, c) => a + c, 0) / b.speeds.length).toFixed(1),
      }));
  })();

  const distributionData = summary
    ? Object.entries(summary.congestion_distribution).map(([level, count]) => ({
        level,
        count,
      }))
    : [];

  const mapCenter = [12.9716, 77.5946]; // Bangalore

  const handleDownloadReport = () => {
    const doc = new jsPDF();

    doc.setFontSize(16);
    doc.text("TrafficVision AI — Analytics Report", 14, 18);
    doc.setFontSize(10);
    doc.setTextColor(100);
    doc.text(`Bangalore · Generated ${new Date().toLocaleString()}`, 14, 25);

    let y = 34;

    if (summary) {
      doc.setFontSize(12);
      doc.setTextColor(0);
      doc.text("City-wide Summary", 14, y);
      autoTable(doc, {
        startY: y + 4,
        head: [["Zones", "Active Incidents", "Predictions (24h)", "Avg Speed", "Busiest Zone"]],
        body: [[
          summary.total_zones,
          summary.active_incidents,
          summary.total_predictions_24h,
          summary.city_avg_speed_kmph ? `${summary.city_avg_speed_kmph} km/h` : "—",
          summary.busiest_zone || "None",
        ]],
        theme: "grid",
        headStyles: { fillColor: [34, 211, 238] },
        styles: { fontSize: 8 },
      });
      y = doc.lastAutoTable.finalY + 10;

      doc.setFontSize(12);
      doc.text("Congestion Distribution", 14, y);
      autoTable(doc, {
        startY: y + 4,
        head: [["Level", "Zone Count"]],
        body: Object.entries(summary.congestion_distribution).map(([lvl, count]) => [
          lvl.toUpperCase(),
          count,
        ]),
        theme: "striped",
        headStyles: { fillColor: [34, 211, 238] },
        styles: { fontSize: 8 },
      });
      y = doc.lastAutoTable.finalY + 10;
    }

    doc.setFontSize(12);
    doc.setTextColor(0);
    doc.text("AI Recommendations", 14, y);
    if (recommendations.length === 0) {
      doc.setFontSize(10);
      doc.setTextColor(120);
      doc.text("No active concerns at time of generation.", 14, y + 8);
      y += 14;
    } else {
      autoTable(doc, {
        startY: y + 4,
        head: [["Severity", "Zone", "Title", "Message"]],
        body: recommendations.map((r) => [
          r.severity.toUpperCase(),
          r.zone_name || "—",
          r.title,
          r.message,
        ]),
        theme: "striped",
        headStyles: { fillColor: [34, 211, 238] },
        styles: { fontSize: 7, cellWidth: "wrap" },
        columnStyles: { 3: { cellWidth: 80 } },
      });
      y = doc.lastAutoTable.finalY + 10;
    }

    if (roadPerformance.length > 0) {
      doc.setFontSize(12);
      doc.setTextColor(0);
      doc.text("Road Performance Tracking (24h)", 14, y);
      autoTable(doc, {
        startY: y + 4,
        head: [["Road Type", "Zones", "Avg Speed", "Avg Vehicles", "Congestion Score", "Most Congested"]],
        body: roadPerformance.map((rp) => [
          rp.road_type.toUpperCase(),
          rp.zone_count,
          `${rp.avg_speed_kmph} km/h`,
          rp.avg_vehicle_count,
          `${rp.avg_congestion_score.toFixed(2)} / 3.0`,
          rp.worst_zone || "—",
        ]),
        theme: "grid",
        headStyles: { fillColor: [34, 211, 238] },
        styles: { fontSize: 7 },
      });
      y = doc.lastAutoTable.finalY + 10;
    }

    doc.setFontSize(12);
    doc.setTextColor(0);
    doc.text("Current Zone Congestion (Heatmap Source Data)", 14, y);
    autoTable(doc, {
      startY: y + 4,
      head: [["Zone", "Congestion Level", "Vehicle Count"]],
      body: heatmap.map((h) => [h.zone_name, h.congestion_level.toUpperCase(), h.vehicle_count ?? "—"]),
      theme: "striped",
      headStyles: { fillColor: [34, 211, 238] },
      styles: { fontSize: 7 },
    });

    doc.save(`trafficvision-analytics-report-${new Date().toISOString().slice(0, 10)}.pdf`);
  };

  return (
    <div className="min-h-screen bg-console-bg">
      <NavBar />
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="mb-6 flex items-start justify-between flex-wrap gap-3">
          <div>
            <h2 className="font-display font-bold text-xl text-console-text">Analytics & Insights</h2>
            <p className="text-console-muted text-sm font-mono mt-1">
              City-wide traffic trends, congestion heatmap, and AI-based recommendations
            </p>
          </div>
          <button
            type="button"
            onClick={handleDownloadReport}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-accent/40 text-accent text-xs font-mono uppercase tracking-wide hover:bg-accent/10 transition-colors shrink-0"
          >
            <span aria-hidden="true">&#8681;</span>
            Download Analytics Report
          </button>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <SummaryCard label="Zones" value={summary?.total_zones ?? "—"} />
          <SummaryCard
            label="Active Incidents"
            value={summary?.active_incidents ?? "—"}
            accent={summary?.active_incidents > 0 ? "text-signal-severe" : undefined}
          />
          <SummaryCard label="Predictions (24h)" value={summary?.total_predictions_24h ?? "—"} />
          <SummaryCard
            label="Avg Speed"
            value={summary?.city_avg_speed_kmph ? `${summary.city_avg_speed_kmph} km/h` : "—"}
          />
          <SummaryCard label="Busiest Zone" value={summary?.busiest_zone ?? "None"} small />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Congestion distribution */}
          <div className="bg-console-panel border border-console-border rounded-lg p-6">
            <h3 className="font-display font-semibold text-console-text text-sm mb-4 uppercase tracking-wide">
              Congestion Distribution
            </h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={distributionData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#232D3A" />
                <XAxis dataKey="level" stroke="#7C8A9A" fontSize={11} />
                <YAxis stroke="#7C8A9A" fontSize={11} allowDecimals={false} />
                <Tooltip contentStyle={{ backgroundColor: "#121821", border: "1px solid #232D3A" }} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {distributionData.map((entry, idx) => (
                    <Cell key={idx} fill={LEVEL_COLORS[entry.level]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Trend chart */}
          <div className="lg:col-span-2 bg-console-panel border border-console-border rounded-lg p-6">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
              <h3 className="font-display font-semibold text-console-text text-sm uppercase tracking-wide">
                Congestion Trend
              </h3>
              <div className="flex gap-2">
                <select
                  value={selectedZoneId}
                  onChange={(e) => setSelectedZoneId(e.target.value)}
                  className="bg-console-bg border border-console-border rounded px-2 py-1 text-console-text text-xs font-mono"
                >
                  <option value="">All zones (avg)</option>
                  {zones.map((z) => (
                    <option key={z.id} value={z.id}>
                      {z.name}
                    </option>
                  ))}
                </select>
                {TREND_WINDOWS.map((w) => (
                  <button
                    key={w.hours}
                    onClick={() => setWindowHours(w.hours)}
                    className={`px-2 py-1 rounded text-xs font-mono uppercase border transition-colors ${
                      windowHours === w.hours
                        ? "border-accent bg-accent/10 text-accent"
                        : "border-console-border text-console-muted hover:text-console-text"
                    }`}
                  >
                    {w.label}
                  </button>
                ))}
              </div>
            </div>

            {chartData.length === 0 ? (
              <div className="h-[200px] flex items-center justify-center text-console-muted text-sm font-body">
                Not enough historical data yet for this window.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#232D3A" />
                  <XAxis dataKey="period" stroke="#7C8A9A" fontSize={10} tick={{ angle: -20 }} height={40} />
                  <YAxis yAxisId="left" stroke="#7C8A9A" fontSize={11} domain={[0, 3]} />
                  <YAxis yAxisId="right" orientation="right" stroke="#7C8A9A" fontSize={11} />
                  <Tooltip contentStyle={{ backgroundColor: "#121821", border: "1px solid #232D3A" }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="congestion_score"
                    name="Congestion (0=low,3=severe)"
                    stroke="#F43F5E"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="avg_speed_kmph"
                    name="Avg Speed (km/h)"
                    stroke="#22D3EE"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Road Performance Tracking */}
        <div className="bg-console-panel border border-console-border rounded-lg p-6 mb-6">
          <h3 className="font-display font-semibold text-console-text text-sm mb-1 uppercase tracking-wide">
            Road Performance Tracking
          </h3>
          <p className="text-console-muted text-xs font-mono mb-4">
            Last 24h, grouped by road type across all zones
          </p>

          {roadPerformance.length === 0 ? (
            <p className="text-console-muted text-sm font-body py-4 text-center">
              Not enough data yet.
            </p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {roadPerformance.map((rp) => (
                <div
                  key={rp.road_type}
                  className="border border-console-border rounded-lg p-4"
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-console-text text-sm font-display font-semibold capitalize">
                      {rp.road_type}
                    </span>
                    <span className="text-console-muted text-[10px] font-mono">
                      {rp.zone_count} zone{rp.zone_count !== 1 ? "s" : ""}
                    </span>
                  </div>

                  {rp.reading_count === 0 ? (
                    <p className="text-console-muted text-xs font-body">No recent readings.</p>
                  ) : (
                    <>
                      <div className="grid grid-cols-2 gap-3 mb-3">
                        <div>
                          <div className="text-console-muted text-[10px] font-mono uppercase">Avg Speed</div>
                          <div className="text-console-text text-lg font-mono font-semibold">
                            {rp.avg_speed_kmph}
                            <span className="text-console-muted text-xs ml-1">km/h</span>
                          </div>
                        </div>
                        <div>
                          <div className="text-console-muted text-[10px] font-mono uppercase">Avg Vehicles</div>
                          <div className="text-console-text text-lg font-mono font-semibold">
                            {rp.avg_vehicle_count}
                          </div>
                        </div>
                      </div>

                      <div className="mb-2">
                        <div className="flex justify-between text-[10px] font-mono text-console-muted mb-1">
                          <span>Congestion score</span>
                          <span>{rp.avg_congestion_score.toFixed(2)} / 3.0</span>
                        </div>
                        <div className="w-full h-1.5 bg-console-bg rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${(rp.avg_congestion_score / 3) * 100}%`,
                              backgroundColor:
                                rp.avg_congestion_score < 1
                                  ? "#34D399"
                                  : rp.avg_congestion_score < 2
                                  ? "#FBBF24"
                                  : "#F43F5E",
                            }}
                          />
                        </div>
                      </div>

                      {rp.worst_zone && (
                        <p className="text-console-muted text-[10px] font-mono mt-2">
                          Most congested: <span className="text-console-text">{rp.worst_zone}</span>
                        </p>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Heatmap */}
          <div className="lg:col-span-2 bg-console-panel border border-console-border rounded-lg overflow-hidden relative" style={{ height: "420px" }}>
            <div className="absolute top-3 right-3 z-[1000] bg-console-panel/95 border border-console-border rounded px-3 py-2 flex items-center gap-3 text-[10px] font-mono uppercase tracking-wide text-console-muted">
              {Object.entries(LEVEL_COLORS).map(([level, color]) => (
                <span key={level} className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                  {level}
                </span>
              ))}
            </div>
            <MapContainer center={mapCenter} zoom={11} style={{ height: "100%", width: "100%" }}>
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              />
              <HeatmapLayer points={heatmap} />
              {heatmap.map((point) => (
                <CircleMarker
                  key={point.zone_id}
                  center={[point.latitude, point.longitude]}
                  radius={5}
                  pathOptions={{
                    color: "#0B0F14",
                    fillColor: LEVEL_COLORS[point.congestion_level],
                    fillOpacity: 0.9,
                    weight: 1,
                  }}
                >
                  <Popup>
                    <strong>{point.zone_name}</strong>
                    <br />
                    {point.congestion_level.toUpperCase()}
                    {point.vehicle_count != null && <> &middot; {point.vehicle_count} vehicles</>}
                  </Popup>
                </CircleMarker>
              ))}
            </MapContainer>
          </div>

          {/* Recommendations */}
          <div className="bg-console-panel border border-console-border rounded-lg p-6">
            <h3 className="font-display font-semibold text-console-text text-sm mb-4 uppercase tracking-wide">
              AI Recommendations
            </h3>
            {recommendations.length === 0 ? (
              <p className="text-console-muted text-sm font-body py-6 text-center">
                No active concerns right now — traffic looks healthy.
              </p>
            ) : (
              <div className="space-y-3 max-h-[320px] overflow-y-auto pr-1">
                {recommendations.map((rec, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded border ${SEVERITY_STYLES[rec.severity] || SEVERITY_STYLES.info}`}
                  >
                    <div className="text-xs font-mono uppercase tracking-wide mb-1">
                      {rec.severity}
                    </div>
                    <div className="text-console-text text-sm font-body font-medium mb-1">
                      {rec.title}
                    </div>
                    <p className="text-console-muted text-xs font-body">{rec.message}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ label, value, accent, small }) {
  return (
    <div className="bg-console-panel border border-console-border rounded-lg p-4">
      <div className="text-console-muted text-[10px] font-mono uppercase tracking-wide mb-1">
        {label}
      </div>
      <div
        className={`font-mono font-semibold ${small ? "text-sm" : "text-xl"} ${
          accent || "text-console-text"
        } truncate`}
      >
        {value}
      </div>
    </div>
  );
}
