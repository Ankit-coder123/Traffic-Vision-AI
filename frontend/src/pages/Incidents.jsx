import { useEffect, useState, useCallback } from "react";
import { incidentsApi, trafficApi } from "../api/client";
import { useAuth } from "../context/AuthContext";

const INCIDENT_TYPES = [
  { value: "accident", label: "Accident" },
  { value: "road_closure", label: "Road Closure" },
  { value: "construction", label: "Construction" },
  { value: "hazard", label: "Hazard" },
  { value: "other", label: "Other" },
];

const SEVERITIES = [
  { value: "minor", label: "Minor" },
  { value: "moderate", label: "Moderate" },
  { value: "major", label: "Major" },
];

const SEVERITY_BADGE = {
  minor: "border-signal-low/40 bg-signal-low/10 text-signal-low",
  moderate: "border-signal-medium/40 bg-signal-medium/10 text-signal-medium",
  major: "border-signal-severe/40 bg-signal-severe/10 text-signal-severe",
};

export default function Incidents() {
  const { user } = useAuth();
  const canReport = user?.role === "admin" || user?.role === "operator";

  const [incidents, setIncidents] = useState([]);
  const [zones, setZones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeOnly, setActiveOnly] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [resolvingId, setResolvingId] = useState(null);
  const [error, setError] = useState(null);

  const [form, setForm] = useState({
    zone_id: "",
    incident_type: "accident",
    severity: "minor",
    description: "",
  });

  const loadData = useCallback(async () => {
    try {
      const [incRes, zoneRes] = await Promise.all([
        incidentsApi.list(activeOnly),
        trafficApi.listZones(),
      ]);
      setIncidents(incRes.data || []);
      setZones(zoneRes.data || []);
    } catch (err) {
      console.error("Failed to load incidents:", err);
      setError("Failed to load data");
    } finally {
      setLoading(false);
    }
  }, [activeOnly]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.zone_id) return;
    setSubmitting(true);
    setError(null);
    try {
      await incidentsApi.create({
        zone_id: parseInt(form.zone_id, 10),
        incident_type: form.incident_type,
        severity: form.severity,
        description: form.description || null,
      });
      setForm({
        zone_id: "",
        incident_type: "accident",
        severity: "minor",
        description: "",
      });
      await loadData();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create incident report");
    } finally {
      setSubmitting(false);
    }
  };

  const handleResolve = async (id, currentResolvedState) => {
    setResolvingId(id);
    try {
      await incidentsApi.resolve(id, !currentResolvedState);
      await loadData();
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to update incident status");
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-display font-bold text-console-text">
          Incident Management
        </h1>
        <p className="text-xs text-console-muted font-mono mt-1">
          Log and track live traffic incidents across monitoring zones.
        </p>
      </div>

      {canReport && (
        <div className="bg-console-panel border border-console-border rounded-lg p-5">
          <h2 className="text-sm font-display font-semibold text-console-text mb-4 uppercase tracking-wider">
            Report New Incident
          </h2>
          {error && (
            <div className="mb-4 p-3 rounded bg-signal-severe/10 border border-signal-severe/30 text-xs text-signal-severe">
              {error}
            </div>
          )}
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-mono text-console-muted mb-1">
                Zone
              </label>
              <select
                value={form.zone_id}
                onChange={(e) => setForm({ ...form, zone_id: e.target.value })}
                required
                className="w-full bg-console-bg border border-console-border rounded px-3 py-2 text-xs text-console-text focus:outline-none focus:border-accent"
              >
                <option value="">Select Zone</option>
                {zones.map((z) => (
                  <option key={z.id} value={z.id}>
                    {z.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-mono text-console-muted mb-1">
                Incident Type
              </label>
              <select
                value={form.incident_type}
                onChange={(e) => setForm({ ...form, incident_type: e.target.value })}
                className="w-full bg-console-bg border border-console-border rounded px-3 py-2 text-xs text-console-text focus:outline-none focus:border-accent"
              >
                {INCIDENT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-mono text-console-muted mb-1">
                Severity
              </label>
              <select
                value={form.severity}
                onChange={(e) => setForm({ ...form, severity: e.target.value })}
                className="w-full bg-console-bg border border-console-border rounded px-3 py-2 text-xs text-console-text focus:outline-none focus:border-accent"
              >
                {SEVERITIES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-mono text-console-muted mb-1">
                Description (Optional)
              </label>
              <input
                type="text"
                placeholder="e.g. 2-car collision blocking right lane"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="w-full bg-console-bg border border-console-border rounded px-3 py-2 text-xs text-console-text focus:outline-none focus:border-accent"
              />
            </div>

            <div className="md:col-span-4 flex justify-end pt-2">
              <button
                type="submit"
                disabled={submitting}
                className="px-5 py-2 rounded bg-accent text-white font-mono text-xs font-semibold hover:bg-accent/80 transition disabled:opacity-50"
              >
                {submitting ? "Logging..." : "Submit Incident Report"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Incident List */}
      <div className="bg-console-panel border border-console-border rounded-lg p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-display font-semibold text-console-text uppercase tracking-wider">
            Incident Log
          </h2>
          <label className="flex items-center gap-2 text-xs font-mono text-console-muted cursor-pointer">
            <input
              type="checkbox"
              checked={activeOnly}
              onChange={(e) => setActiveOnly(e.target.checked)}
              className="rounded border-console-border bg-console-bg"
            />
            Active Only
          </label>
        </div>

        {loading ? (
          <p className="text-xs font-mono text-console-muted py-6 text-center">
            Loading incidents...
          </p>
        ) : incidents.length === 0 ? (
          <p className="text-xs font-mono text-console-muted py-6 text-center">
            No incidents found.
          </p>
        ) : (
          <div className="space-y-3">
            {incidents.map((inc) => {
              const isResolved = Boolean(inc.is_resolved);
              const severityKey = (inc.severity || "minor").toLowerCase();

              return (
                <div
                  key={inc.id}
                  className={`p-4 rounded-lg border transition flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                    isResolved
                      ? "bg-console-bg/30 border-console-border opacity-60"
                      : "bg-console-bg border-console-border"
                  }`}
                >
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-semibold text-console-text font-display">
                        {inc.incident_type?.replace("_", " ").toUpperCase()}
                      </span>
                      <span className="text-xs text-console-muted">&middot;</span>
                      <span className="text-xs text-console-muted font-body">
                        {inc.zone_name || `Zone #${inc.zone_id}`}
                      </span>

                      <span
                        className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${
                          SEVERITY_BADGE[severityKey] || "border-console-border"
                        }`}
                      >
                        {inc.severity}
                      </span>

                      {isResolved && (
                        <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border border-console-border bg-white/5 text-console-muted">
                          Resolved
                        </span>
                      )}
                    </div>

                    {inc.description && (
                      <p className="text-xs text-console-text font-body">
                        {inc.description}
                      </p>
                    )}

                    <div className="text-[10px] font-mono text-console-muted">
                      Reported: {new Date(inc.created_at).toLocaleString()}
                    </div>
                  </div>

                  {canReport && (
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => handleResolve(inc.id, isResolved)}
                        disabled={resolvingId === inc.id}
                        className={`px-3 py-1.5 rounded font-mono text-xs border transition disabled:opacity-50 ${
                          isResolved
                            ? "border-console-border text-console-muted hover:text-console-text"
                            : "border-signal-severe/40 text-signal-severe hover:bg-signal-severe/10"
                        }`}
                      >
                        {resolvingId === inc.id
                          ? "Updating..."
                          : isResolved
                          ? "Reopen"
                          : "Mark Resolved"}
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}