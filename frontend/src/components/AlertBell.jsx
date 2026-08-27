import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { incidentsApi } from "../api/client";

const SEVERITY_DOT = {
  major: "bg-signal-severe",
  critical: "bg-signal-severe",
  moderate: "bg-signal-medium",
  warning: "bg-signal-medium",
  minor: "bg-signal-low",
  info: "bg-accent",
};

export default function AlertBell() {
  const [incidents, setIncidents] = useState([]);
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
    incidentsApi
      .list(true)
      .then((res) => setIncidents(res.data || []))
      .catch(() => {});
  };

  const totalCount = incidents.length;
  const hasCritical = incidents.some(
    (i) => i.severity === "major" || i.severity === "critical"
  );

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
        <div className="absolute right-0 mt-2 w-80 bg-console-panel border border-console-border rounded-lg shadow-xl z-50 max-h-[400px] overflow-y-auto origin-top-right animate-fade-in-scale">
          <div className="px-4 py-3 border-b border-console-border">
            <h4 className="text-console-text text-sm font-display font-semibold">
              Incident Alerts
            </h4>
            <p className="text-console-muted text-[10px] font-mono">
              {totalCount === 0 ? "All clear" : `${totalCount} active`}
            </p>
          </div>

          {totalCount === 0 ? (
            <div className="px-4 py-6 text-center text-console-muted text-sm font-body">
              No active incident reports.
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
                      className={`w-2 h-2 rounded-full mt-1 shrink-0 ${
                        SEVERITY_DOT[inc.severity] || "bg-console-muted"
                      }`}
                    />
                    <div className="min-w-0">
                      <div className="text-console-text text-xs font-body font-medium truncate">
                        {inc.incident_type?.replace("_", " ")} &middot;{" "}
                        {inc.zone_name || `Zone #${inc.zone_id}`}
                      </div>
                      <div className="text-console-muted text-[10px] font-mono mt-0.5">
                        {inc.severity?.toUpperCase()}
                        {inc.created_at
                          ? ` · ${new Date(inc.created_at).toLocaleTimeString()}`
                          : ""}
                      </div>
                    </div>
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