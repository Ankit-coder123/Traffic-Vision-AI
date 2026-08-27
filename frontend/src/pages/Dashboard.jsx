import { useEffect, useState, useCallback } from "react";
import { trafficApi, analyticsApi } from "../api/client";
import ZoneCard from "../components/ZoneCard";
import NavBar from "../components/NavBar";
import { Skeleton } from "../components/Skeleton";

const POLL_INTERVAL_MS = 5000;

// const STATUS_STYLES = {
//   closed: "bg-signal-severe/10 text-signal-severe border-signal-severe/30",
//   impaired: "bg-signal-high/10 text-signal-high border-signal-high/30",
//   congested: "bg-signal-medium/10 text-signal-medium border-signal-medium/30",
// };
const STATUS_LABELS = { closed: "Closed", impaired: "Impaired", congested: "Congested" };

export default function Dashboard() {
  const [zones, setZones] = useState([]);
  const [readingsByZone, setReadingsByZone] = useState({});
  const [error, setError] = useState("");
  const [lastSync, setLastSync] = useState(null);
  const [roadConditions, setRoadConditions] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [zonesRes, liveRes] = await Promise.all([
        trafficApi.getZones(),
        trafficApi.getLive(),
      ]);
      setZones(zonesRes.data);

      const map = {};
      liveRes.data.forEach((reading) => {
        map[reading.zone_id] = reading;
      });
      setReadingsByZone(map);
      setLastSync(new Date());
      setError("");
    } catch (err) {
      setError(
        "Lost connection to the monitoring feed. Retrying automatically..."
      );
    }
    setLoading(false);
    analyticsApi.getRoadConditions().then((res) => setRoadConditions(res.data)).catch(() => {});
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Quick summary counts for the header strip
  const counts = zones.reduce(
    (acc, zone) => {
      const level = readingsByZone[zone.id]?.congestion_level || "low";
      acc[level] = (acc[level] || 0) + 1;
      return acc;
    },
    { low: 0, medium: 0, high: 0, severe: 0 }
  );

  return (
    <div className="min-h-screen bg-console-bg">
      <NavBar />

      <main className="max-w-6xl mx-auto px-6 py-8 animate-fade-in">
        {/* Status strip */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex gap-4 text-xs font-mono">
            <StatusPill label="Flowing" count={counts.low} colorClass="text-signal-low" />
            <StatusPill label="Moderate" count={counts.medium} colorClass="text-signal-medium" />
            <StatusPill label="Heavy" count={counts.high} colorClass="text-signal-high" />
            <StatusPill label="Gridlock" count={counts.severe} colorClass="text-signal-severe" />
          </div>
          <div className="text-console-muted text-xs font-mono">
            {lastSync
              ? `Synced ${lastSync.toLocaleTimeString()}`
              : "Connecting..."}
          </div>
        </div>

        {error && (
          <div className="mb-6 px-4 py-3 rounded bg-signal-severe/10 border border-signal-severe/30 text-signal-severe text-sm font-body">
            {error}
          </div>
        )}

        {/* Road Condition Monitoring -- only surfaces zones that need attention */}
        {roadConditions.filter((r) => r.status !== "normal").length > 0 && (
          <div className="mb-6 bg-console-panel border border-console-border rounded-lg p-4">
            <h3 className="font-display font-semibold text-console-text text-xs uppercase tracking-wide mb-3">
              Road Conditions Needing Attention
            </h3>
            <div className="flex flex-col gap-2">
              {roadConditions
                .filter((r) => r.status !== "normal")
                .map((r) => (
                  <div key={r.zone_id} className="flex items-center justify-between text-sm font-body">
                    <span className="text-console-text">{r.zone_name}</span>
                    <div className="flex items-center gap-2">
                      {r.active_incident_type && (
                        <span className="text-console-muted text-xs font-mono capitalize">
                          {r.active_incident_type.replace("_", " ")}
                        </span>
                      )}
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wide border ${STATUS_STYLES[r.status]}`}
                      >
                        {STATUS_LABELS[r.status]}
                      </span>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}

        {zones.length === 0 && !error && !loading && (
          <div className="text-center py-20">
            <p className="text-console-muted font-body text-sm">
              No traffic zones yet. Run{" "}
              <code className="text-accent">simulator.py</code> to seed live
              data.
            </p>
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonZoneCard key={i} />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {zones.map((zone, index) => (
              <ZoneCard
                key={zone.id}
                zoneName={zone.name}
                reading={readingsByZone[zone.id]}
                index={index}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function SkeletonZoneCard() {
  return (
    <div className="bg-console-panel border border-console-border rounded-lg p-4">
      <div className="flex items-start justify-between mb-3">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="w-2 h-2 rounded-full shrink-0 mt-1" />
      </div>
      <Skeleton className="h-4 w-16 mb-4" />
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Skeleton className="h-2.5 w-14 mb-1.5" />
          <Skeleton className="h-6 w-10" />
        </div>
        <div>
          <Skeleton className="h-2.5 w-14 mb-1.5" />
          <Skeleton className="h-6 w-14" />
        </div>
      </div>
    </div>
  );
}

function StatusPill({ label, count, colorClass }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className={`${colorClass} font-semibold tabular-nums`}>{count}</span>
      <span className="text-console-muted uppercase tracking-wide">{label}</span>
    </div>
  );
}
