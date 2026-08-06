import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { incidentsApi, analyticsApi } from "../api/client";
import { useAuth } from "../context/AuthContext";

const SEVERITY_DOT = {
  major: "bg-signal-severe",
  critical: "bg-signal-severe",
  moderate: "bg-signal-medium",
  warning: "bg-signal-medium",
  minor: "bg-signal-low",
  info: "bg-accent",
};

export default function AlertBell() {
  const { user } = useAuth();
  const canDismiss = user?.role === "admin" || user?.role === "operator";

  const [incidents, setIncidents] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [dismissingZoneId, setDismissingZoneId] = useState(null);
  const [open, setOpen] = useState(false);
  const panelRef = useRef(null);

  useEffect(() => {
    loadAlerts();
    const interval = setInterval(loadAlerts, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const loadAlerts = () => {
    incidentsApi.list(true).then((res) => setIncidents(res.data)).catch(() => {});
    analyticsApi
      .getRecommendations()
      .then((res) =>
        setRecommendations(
          // Only count congestion-pattern recommendations here. Incident-derived
          // recommendations ('source: incident') describe the exact same event
          // already listed in `incidents` above -- merging both would count one
          // real-world incident as two separate alerts.
          res.data.filter((r) => r.severity !== "info" && r.source === "congestion")
        )
      )
      .catch(() => {});
  };

  const handleDismiss = async (e, zoneId) => {
    e.preventDefault();
    e.stopPropagation();
    if (!zoneId || dismissingZoneId === zoneId) return;
    setDismissingZoneId(zoneId);
    try {
      await analyticsApi.dismissRecommendation(zoneId);
      // Optimistically drop every recommendation for this zone (there's at
      // most one congestion recommendation per zone) instead of waiting for
      // the next 15s poll.
      setRecommendations((prev) => prev.filter((r) => r.zone_id !== zoneId));
    } catch (err) {
      // no-op -- alert simply reappears on next poll if dismiss failed
    } finally {
      setDismissingZoneId(null);
    }
  };

  const totalCount = incidents.length + recommendations.length;
  const hasCritical =
    incidents.some((i) => i.severity === "major") ||
    recommendations.some((r) => r.severity === "critical");

  return (
    <div className="relative" ref={panelRef}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative text-console-muted hover:text-console-text border border-console-border rounded px-2.5 py-1.5 hover:border-accent/50 transition-colors"
        aria-label="Alerts"
      >
        <span className="text-sm">&#128276;</span>
        {totalCount > 0 && (
          <span
            className={`absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-mono flex items-center justify-center text-console-bg font-bold ${
              hasCritical ? "bg-signal-severe" : "bg-signal-medium"
            }`}
          >
            {totalCount > 9 ? "9+" : totalCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-console-panel border border-console-border rounded-lg shadow-xl z-50 max-h-[400px] overflow-y-auto">
          <div className="px-4 py-3 border-b border-console-border">
            <h4 className="text-console-text text-sm font-display font-semibold">Alerts</h4>
            <p className="text-console-muted text-[10px] font-mono">
              {totalCount === 0 ? "All clear" : `${totalCount} active`}
            </p>
          </div>

          {totalCount === 0 ? (
            <div className="px-4 py-6 text-center text-console-muted text-sm font-body">
              No active alerts right now.
            </div>
          ) : (
            <div className="divide-y divide-console-border">
              {incidents.map((inc) => (
                <Link
                  key={`inc-${inc.id}`}
                  to="/incidents"
                  onClick={() => setOpen(false)}
                  className="block px-4 py-3 hover:bg-console-bg/50 transition-colors"
                >
                  <div className="flex items-start gap-2">
                    <span
                      className={`w-2 h-2 rounded-full mt-1 shrink-0 ${SEVERITY_DOT[inc.severity] || "bg-console-muted"}`}
                    />
                    <div className="min-w-0">
                      <div className="text-console-text text-xs font-body font-medium truncate">
                        {inc.incident_type.replace("_", " ")} &middot; {inc.zone_name}
                      </div>
                      <div className="text-console-muted text-[10px] font-mono mt-0.5">
                        {inc.severity.toUpperCase()} &middot; {new Date(inc.created_at).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
              {recommendations.map((rec, idx) => (
                <Link
                  key={`rec-${idx}`}
                  to="/analytics"
                  onClick={() => setOpen(false)}
                  className="block px-4 py-3 hover:bg-console-bg/50 transition-colors"
                >
                  <div className="flex items-start gap-2">
                    <span
                      className={`w-2 h-2 rounded-full mt-1 shrink-0 ${SEVERITY_DOT[rec.severity] || "bg-console-muted"}`}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="text-console-text text-xs font-body font-medium truncate">
                        {rec.title}
                      </div>
                      <div className="text-console-muted text-[10px] font-mono mt-0.5 truncate">
                        {rec.message}
                      </div>
                    </div>
                    {canDismiss && (
                      <button
                        onClick={(e) => handleDismiss(e, rec.zone_id)}
                        disabled={dismissingZoneId === rec.zone_id}
                        title="Dismiss for 30 minutes"
                        className="shrink-0 text-[10px] font-mono uppercase tracking-wide text-console-muted hover:text-console-text hover:underline disabled:opacity-40"
                      >
                        {dismissingZoneId === rec.zone_id ? "..." : "Dismiss"}
                      </button>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
