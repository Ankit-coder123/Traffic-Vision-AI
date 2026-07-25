import { useEffect, useState, useCallback } from "react";
import { trafficApi } from "../api/client";
import ZoneCard from "../components/ZoneCard";
import NavBar from "../components/NavBar";

const POLL_INTERVAL_MS = 5000;

export default function Dashboard() {
  const [zones, setZones] = useState([]);
  const [readingsByZone, setReadingsByZone] = useState({});
  const [error, setError] = useState("");
  const [lastSync, setLastSync] = useState(null);

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

      <main className="max-w-6xl mx-auto px-6 py-8">
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

        {zones.length === 0 && !error && (
          <div className="text-center py-20">
            <p className="text-console-muted font-body text-sm">
              No traffic zones yet. Run{" "}
              <code className="text-accent">simulator.py</code> to seed live
              data.
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {zones.map((zone) => (
            <ZoneCard
              key={zone.id}
              zoneName={zone.name}
              reading={readingsByZone[zone.id]}
            />
          ))}
        </div>
      </main>
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
