import { useEffect, useState } from "react";
import { incidentsApi, trafficApi } from "../api/client";
import { useAuth } from "../context/AuthContext";
import NavBar from "../components/NavBar";
import { Skeleton } from "../components/Skeleton";

const INCIDENT_TYPES = [
  { value: "accident", label: "Accident" },
  { value: "road_closure", label: "Road Closure" },
  { value: "construction", label: "Construction" },
  { value: "hazard", label: "Hazard" },
  { value: "other", label: "Other" },
];

const SEVERITY_STYLES = {
  minor: "bg-signal-medium/10 text-signal-medium border-signal-medium/30",
  moderate: "bg-signal-high/10 text-signal-high border-signal-high/30",
  major: "bg-signal-severe/10 text-signal-severe border-signal-severe/30",
};

export default function Incidents() {
  const { user } = useAuth();
  const canReport = user?.role === "admin" || user?.role === "operator";

  const [zones, setZones] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [form, setForm] = useState({
    zone_id: "",
    incident_type: "accident",
    severity: "minor",
    description: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [incidentsLoading, setIncidentsLoading] = useState(true);

  useEffect(() => {
    trafficApi.getZones().then((res) => setZones(res.data)).catch(() => {});
    incidentsApi
      .list(true)
      .then((res) => setIncidents(res.data))
      .catch(() => {})
      .finally(() => setIncidentsLoading(false));
  }, []);

  const loadIncidents = () => {
    incidentsApi
      .list(true)
      .then((res) => setIncidents(res.data))
      .catch(() => {});
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!form.zone_id) {
      setError("Select a zone.");
      return;
    }
    setSubmitting(true);
    try {
      await incidentsApi.report({
        zone_id: Number(form.zone_id),
        incident_type: form.incident_type,
        severity: form.severity,
        description: form.description || null,
      });
      setForm((prev) => ({ ...prev, description: "" }));
      loadIncidents();
    } catch (err) {
      setError(err.response?.data?.detail ? String(err.response.data.detail) : "Failed to report incident.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleResolve = async (id) => {
    try {
      await incidentsApi.resolve(id);
      loadIncidents();
    } catch (err) {
      // no-op -- list simply won't update if this fails
    }
  };

  return (
    <div className="min-h-screen bg-console-bg">
      <NavBar />
      <div className="max-w-6xl mx-auto px-6 py-8 animate-fade-in">
        <div className="mb-6">
          <h2 className="font-display font-bold text-xl text-console-text">Incidents</h2>
          <p className="text-console-muted text-sm font-mono mt-1">
            {canReport
              ? "Report and track real-world incidents across the Bangalore network"
              : "Active incidents currently affecting the Bangalore network"}
          </p>
        </div>

        <div className={`grid grid-cols-1 ${canReport ? "lg:grid-cols-3" : ""} gap-6`}>
          {canReport && (
            <form
              onSubmit={handleSubmit}
              className="lg:col-span-1 bg-console-panel border border-console-border rounded-lg p-6 h-fit"
            >
              <h3 className="font-display font-semibold text-console-text text-sm mb-4 uppercase tracking-wide">
                Report Incident
              </h3>

              <label className="block mb-4">
                <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
                  Zone
                </span>
                <select
                  value={form.zone_id}
                  onChange={(e) => setForm((p) => ({ ...p, zone_id: e.target.value }))}
                  className="w-full bg-console-bg border border-console-border rounded px-3 py-2.5 text-console-text focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent font-body text-sm"
                >
                  <option value="">Select zone</option>
                  {zones.map((z) => (
                    <option key={z.id} value={z.id}>
                      {z.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block mb-4">
                <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
                  Type
                </span>
                <select
                  value={form.incident_type}
                  onChange={(e) => setForm((p) => ({ ...p, incident_type: e.target.value }))}
                  className="w-full bg-console-bg border border-console-border rounded px-3 py-2.5 text-console-text focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent font-body text-sm"
                >
                  {INCIDENT_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </label>

              <div className="mb-4">
                <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
                  Severity
                </span>
                <div className="grid grid-cols-3 gap-2">
                  {["minor", "moderate", "major"].map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => setForm((p) => ({ ...p, severity: s }))}
                      className={`px-2 py-2 rounded border text-xs font-mono uppercase tracking-wide transition-colors ${
                        form.severity === s
                          ? SEVERITY_STYLES[s]
                          : "border-console-border text-console-muted hover:text-console-text"
                      }`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              <label className="block mb-4">
                <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
                  Description (optional)
                </span>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                  placeholder="Brief details..."
                  rows={3}
                  className="w-full bg-console-bg border border-console-border rounded px-3 py-2.5 text-console-text placeholder:text-console-muted/50 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent font-body text-sm resize-none"
                />
              </label>

              {error && (
                <div className="mb-4 px-3 py-2 rounded bg-signal-severe/10 border border-signal-severe/30 text-signal-severe text-sm font-body">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="w-full bg-accent text-console-bg font-display font-semibold rounded py-2.5 text-sm tracking-wide hover:bg-accent/90 active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100 transition"
              >
                {submitting ? "Reporting..." : "Report Incident"}
              </button>
            </form>
          )}

          <div className={canReport ? "lg:col-span-2" : ""}>
            <div className="bg-console-panel border border-console-border rounded-lg p-6">
              <h3 className="font-display font-semibold text-console-text text-sm mb-4 uppercase tracking-wide">
                Active Incidents ({incidents.length})
              </h3>

              {incidentsLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <SkeletonIncidentRow key={i} />
                  ))}
                </div>
              ) : incidents.length === 0 ? (
                <p className="text-console-muted text-sm font-body py-6 text-center">
                  No active incidents reported right now.
                </p>
              ) : (
                <div className="space-y-3">
                  {incidents.map((inc) => (
                    <div
                      key={inc.id}
                      className="p-3 rounded border border-console-border flex items-start justify-between gap-3"
                    >
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wide border ${SEVERITY_STYLES[inc.severity]}`}
                          >
                            {inc.severity}
                          </span>
                          <span className="text-console-text text-sm font-body font-medium">
                            {INCIDENT_TYPES.find((t) => t.value === inc.incident_type)?.label || inc.incident_type}
                          </span>
                        </div>
                        <p className="text-console-muted text-xs font-mono">{inc.zone_name}</p>
                        {inc.description && (
                          <p className="text-console-text text-xs font-body mt-1">{inc.description}</p>
                        )}
                        <p className="text-console-muted text-[10px] font-mono mt-1">
                          Reported {new Date(inc.created_at).toLocaleString()}
                        </p>
                      </div>
                      {canReport && (
                        <button
                          onClick={() => handleResolve(inc.id)}
                          className="shrink-0 text-[10px] font-mono uppercase tracking-wide text-signal-low hover:underline"
                        >
                          Mark Resolved
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SkeletonIncidentRow() {
  return (
    <div className="p-3 rounded border border-console-border flex items-start justify-between gap-3">
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-2">
          <Skeleton className="h-4 w-14" />
          <Skeleton className="h-4 w-28" />
        </div>
        <Skeleton className="h-3 w-20 mb-1.5" />
        <Skeleton className="h-2.5 w-32" />
      </div>
      <Skeleton className="h-3 w-16 shrink-0" />
    </div>
  );
}
