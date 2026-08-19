import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { routesApi, trafficApi } from "../api/client";
import NavBar from "../components/NavBar";

// Leaflet's default marker icons break under bundlers like Vite unless
// re-pointed explicitly at the packaged asset URLs -- a well-known Leaflet +
// bundler gotcha, not a config mistake.
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const ROUTE_COLORS = ["#22D3EE", "#7C8A9A", "#FB923C"]; // recommended, then alternates

// Re-centers/zooms the map to fit whichever route is currently selected.
// Must live inside <MapContainer> to access the map instance via useMap().
function FitBoundsToRoute({ geometry }) {
  const map = useMap();
  useEffect(() => {
    if (geometry && geometry.length > 0) {
      map.fitBounds(geometry, { padding: [40, 40] });
    }
  }, [geometry, map]);
  return null;
}

// Rough illustrative emission factor for an average passenter car (grams
// CO2 per km). Not derived from real vehicle telemetry -- presented as an
// estimate to make the "smart city" efficiency angle tangible, not as a
// precise measurement.
const CO2_GRAMS_PER_KM = 170;

function RouteComparisonSummary({ routes }) {
  const fastest = routes.reduce((a, b) => (a.estimated_duration_min <= b.estimated_duration_min ? a : b));
  const slowest = routes.reduce((a, b) => (a.estimated_duration_min >= b.estimated_duration_min ? a : b));

  const timeSavedMin = +(slowest.estimated_duration_min - fastest.estimated_duration_min).toFixed(1);
  const distanceDeltaKm = +(slowest.distance_km - fastest.distance_km).toFixed(2);
  const co2SavedG = Math.round(distanceDeltaKm * CO2_GRAMS_PER_KM);

  if (timeSavedMin <= 0) return null;

  return (
    <div className="mb-4 p-3 rounded border border-signal-low/30 bg-signal-low/5">
      <div className="text-xs font-mono text-signal-low uppercase tracking-wide mb-1">
        Fastest route saves
      </div>
      <div className="flex items-baseline gap-4">
        <div>
          <span className="text-lg font-mono text-console-text font-semibold">{timeSavedMin}</span>
          <span className="text-console-muted text-xs font-mono ml-1">min</span>
        </div>
        {co2SavedG !== 0 && (
          <div>
            <span className="text-lg font-mono text-console-text font-semibold">
              {Math.abs(co2SavedG)}
            </span>
            <span className="text-console-muted text-xs font-mono ml-1">
              g CO&#8322; {co2SavedG > 0 ? "saved" : "extra"} (est.)
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Routes() {
  const location = useLocation();
  const navigate = useNavigate();
  const [zones, setZones] = useState([]);
  const [originId, setOriginId] = useState(location.state?.originId ? String(location.state.originId) : "");
  const [destinationId, setDestinationId] = useState(
    location.state?.destinationId ? String(location.state.destinationId) : ""
  );
  const [result, setResult] = useState(null);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [cameFromPrediction] = useState(Boolean(location.state?.autoSearch));

  const [savedRoutes, setSavedRoutes] = useState([]);
  const [saveLabel, setSaveLabel] = useState("");
  const [savingRoute, setSavingRoute] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");

  useEffect(() => {
    trafficApi.getZones().then((res) => setZones(res.data)).catch(() => {});
    loadSavedRoutes();

    // Arrived here from the Prediction page with a route already chosen --
    // run the search automatically instead of making the person click again.
    if (location.state?.autoSearch && location.state?.originId && location.state?.destinationId) {
      findRoutes(location.state.originId, location.state.destinationId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadSavedRoutes = () => {
    routesApi
      .getSavedRoutes()
      .then((res) => setSavedRoutes(res.data))
      .catch(() => {});
  };

  const findRoutes = async (originZoneId, destinationZoneId) => {
    setError("");
    setResult(null);
    setLoading(true);
    try {
      const res = await routesApi.optimize({
        origin_zone_id: Number(originZoneId),
        destination_zone_id: Number(destinationZoneId),
      });
      setResult(res.data);
      const recommendedIdx = res.data.routes.findIndex((r) => r.is_recommended);
      setSelectedIdx(recommendedIdx >= 0 ? recommendedIdx : 0);
    } catch (err) {
      setError(
        err.response?.data?.detail
          ? String(err.response.data.detail)
          : "Route lookup failed. Check that the backend is running and has internet access to reach the routing service."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleSaveCurrentRoute = async () => {
    if (!saveLabel.trim()) return;
    setSavingRoute(true);
    setSaveMessage("");
    try {
      await routesApi.saveRoute({
        label: saveLabel.trim(),
        origin_zone_id: Number(originId),
        destination_zone_id: Number(destinationId),
      });
      setSaveLabel("");
      setSaveMessage("Saved!");
      loadSavedRoutes();
      setTimeout(() => setSaveMessage(""), 2000);
    } catch {
      setSaveMessage("Failed to save.");
    } finally {
      setSavingRoute(false);
    }
  };

  const handleLoadSavedRoute = (saved) => {
    setOriginId(String(saved.origin_zone_id));
    setDestinationId(String(saved.destination_zone_id));
    findRoutes(saved.origin_zone_id, saved.destination_zone_id);
  };

  const handleDeleteSavedRoute = async (id) => {
    try {
      await routesApi.deleteSavedRoute(id);
      loadSavedRoutes();
    } catch {
      // no-op
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setResult(null);

    if (!originId || !destinationId) {
      setError("Select both an origin and a destination zone.");
      return;
    }
    if (originId === destinationId) {
      setError("Origin and destination must be different zones.");
      return;
    }

    findRoutes(originId, destinationId);
  };

  const mapCenter = result
    ? [result.origin.lat, result.origin.lng]
    : [12.9716, 77.5946]; // fallback center (Bangalore) until a route is loaded

  const selectedRoute = result?.routes[selectedIdx];

  return (
    <div className="min-h-screen bg-console-bg">
      <NavBar />
      <div className="max-w-6xl mx-auto px-6 py-8 animate-fade-in">
        <div className="mb-6">
          <h2 className="font-display font-bold text-xl text-console-text">
            Route Optimization
          </h2>
          <p className="text-console-muted text-sm font-mono mt-1">
            Alternate routes via OSRM, ranked by congestion-adjusted travel time
            {result && " — click a route below to view it on the map"}
          </p>
        </div>

        {cameFromPrediction && location.state?.predictedCongestion && (
          <div className="mb-6 px-4 py-3 rounded-lg border border-accent/30 bg-accent/5 flex items-center gap-2 text-sm font-body">
            <span className="text-accent font-mono uppercase tracking-wide text-xs">
              Predicted
            </span>
            <span
              className={
                location.state.predictedCongestion === "high"
                  ? "text-signal-high font-semibold uppercase"
                  : location.state.predictedCongestion === "medium"
                  ? "text-signal-medium font-semibold uppercase"
                  : "text-signal-low font-semibold uppercase"
              }
            >
              {location.state.predictedCongestion} congestion
            </span>
            <span className="text-console-muted">for this route — here are your optimized alternatives</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Controls + route list */}
          <div className="lg:col-span-1 space-y-6">
            <form
              onSubmit={handleSubmit}
              className="bg-console-panel border border-console-border rounded-lg p-6"
            >
              <label className="block mb-4">
                <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
                  From
                </span>
                <select
                  value={originId}
                  onChange={(e) => setOriginId(e.target.value)}
                  className="w-full bg-console-bg border border-console-border rounded px-3 py-2.5 text-console-text focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent font-body text-sm"
                >
                  <option value="">Select origin zone</option>
                  {zones.map((z) => (
                    <option key={z.id} value={z.id}>
                      {z.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block mb-6">
                <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
                  To
                </span>
                <select
                  value={destinationId}
                  onChange={(e) => setDestinationId(e.target.value)}
                  className="w-full bg-console-bg border border-console-border rounded px-3 py-2.5 text-console-text focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent font-body text-sm"
                >
                  <option value="">Select destination zone</option>
                  {zones.map((z) => (
                    <option key={z.id} value={z.id}>
                      {z.name}
                    </option>
                  ))}
                </select>
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
                {loading ? "Finding routes..." : "Find Routes"}
              </button>

              {result && (
                <div className="mt-4 pt-4 border-t border-console-border">
                  <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
                    Save this route
                  </span>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={saveLabel}
                      onChange={(e) => setSaveLabel(e.target.value)}
                      placeholder="e.g. Home to Office"
                      className="flex-1 bg-console-bg border border-console-border rounded px-3 py-2 text-console-text placeholder:text-console-muted/50 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent font-body text-sm"
                    />
                    <button
                      type="button"
                      onClick={handleSaveCurrentRoute}
                      disabled={!saveLabel.trim() || savingRoute}
                      className="px-3 py-2 rounded border border-accent/40 text-accent text-xs font-mono uppercase tracking-wide hover:bg-accent/10 disabled:opacity-40 transition-colors shrink-0"
                    >
                      {savingRoute ? "..." : "Save"}
                    </button>
                  </div>
                  {saveMessage && (
                    <p className="text-console-muted text-[10px] font-mono mt-1.5">{saveMessage}</p>
                  )}
                </div>
              )}
            </form>

            {savedRoutes.length > 0 && (
              <div className="bg-console-panel border border-console-border rounded-lg p-6">
                <h3 className="font-display font-semibold text-console-text text-sm mb-4 uppercase tracking-wide">
                  My Saved Routes
                </h3>
                <div className="space-y-2">
                  {savedRoutes.map((s) => (
                    <div
                      key={s.id}
                      className="flex items-center justify-between gap-2 p-2.5 rounded border border-console-border hover:border-accent/40 transition-colors"
                    >
                      <button
                        type="button"
                        onClick={() => handleLoadSavedRoute(s)}
                        className="text-left flex-1 min-w-0"
                      >
                        <div className="text-console-text text-sm font-body font-medium truncate">
                          {s.label}
                        </div>
                        <div className="text-console-muted text-[10px] font-mono truncate">
                          {s.origin_zone_name} &rarr; {s.destination_zone_name}
                        </div>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteSavedRoute(s.id)}
                        className="shrink-0 text-console-muted hover:text-signal-severe text-xs font-mono px-1.5"
                        title="Delete"
                      >
                        &times;
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result && result.incident_warnings && result.incident_warnings.length > 0 && (
              <div className="bg-signal-severe/10 border border-signal-severe/40 rounded-lg p-4">
                <div className="flex items-center gap-1.5 mb-2">
                  <span className="text-signal-severe">&#9888;</span>
                  <h4 className="text-signal-severe text-xs font-mono uppercase tracking-wide font-semibold">
                    Active Incident Alert
                  </h4>
                </div>
                <ul className="space-y-1.5">
                  {result.incident_warnings.map((warning, idx) => (
                    <li key={idx} className="text-console-text text-xs font-body">
                      {warning}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {result && (
              <div className="bg-console-panel border border-console-border rounded-lg p-6">
                <div className="flex items-center justify-between mb-1">
                  <h3 className="font-display font-semibold text-console-text text-sm uppercase tracking-wide">
                    Route Options
                  </h3>
                  <button
                    type="button"
                    onClick={() =>
                      navigate("/prediction", {
                        state: { originId, destinationId },
                      })
                    }
                    className="text-[10px] font-mono text-accent hover:underline uppercase tracking-wide shrink-0"
                  >
                    Predict Congestion &rarr;
                  </button>
                </div>
                <p className="text-console-muted text-xs font-mono mb-4">
                  City-wide congestion: {result.congestion_level_used}
                </p>

                {result.routes.length > 1 && (
                  <RouteComparisonSummary routes={result.routes} />
                )}

                <div className="space-y-3">
                  {result.routes.map((route, idx) => {
                    const isSelected = idx === selectedIdx;
                    return (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => setSelectedIdx(idx)}
                        className={`w-full text-left p-3 rounded border transition-colors cursor-pointer ${
                          isSelected
                            ? "border-accent bg-accent/10 ring-1 ring-accent/40"
                            : route.is_recommended
                            ? "border-accent/30 bg-accent/5 hover:border-accent/50"
                            : "border-console-border hover:border-console-border/80 hover:bg-console-bg/50"
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span
                            className="text-xs font-mono uppercase tracking-wide flex items-center gap-1.5"
                            style={{ color: ROUTE_COLORS[idx % ROUTE_COLORS.length] }}
                          >
                            <span
                              className="w-2 h-2 rounded-full inline-block"
                              style={{ backgroundColor: ROUTE_COLORS[idx % ROUTE_COLORS.length] }}
                            />
                            Route {idx + 1}
                            {route.is_recommended && " — Recommended"}
                          </span>
                          {isSelected && (
                            <span className="text-[10px] font-mono text-accent uppercase tracking-wide">
                              Viewing
                            </span>
                          )}
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-sm font-mono text-console-text">
                          <div>
                            <div className="text-console-muted text-[10px]">Distance</div>
                            {route.distance_km} km
                          </div>
                          <div>
                            <div className="text-console-muted text-[10px]">Base ETA</div>
                            {route.base_duration_min} min
                          </div>
                          <div>
                            <div className="text-console-muted text-[10px]">Adjusted ETA</div>
                            <span className={route.is_recommended ? "text-accent" : ""}>
                              {route.estimated_duration_min} min
                            </span>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Map */}
          <div className="lg:col-span-2 bg-console-panel border border-console-border rounded-lg overflow-hidden" style={{ height: "600px" }}>
            <MapContainer
              center={mapCenter}
              zoom={result ? 13 : 11}
              style={{ height: "100%", width: "100%" }}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              />

              {result && (
                <>
                  <Marker position={[result.origin.lat, result.origin.lng]}>
                    <Popup>Origin</Popup>
                  </Marker>
                  <Marker position={[result.destination.lat, result.destination.lng]}>
                    <Popup>Destination</Popup>
                  </Marker>

                  {/* Draw non-selected routes first (dimmed), selected route last so it renders on top */}
                  {result.routes.map((route, idx) =>
                    idx === selectedIdx ? null : (
                      <Polyline
                        key={idx}
                        positions={route.geometry}
                        pathOptions={{
                          color: ROUTE_COLORS[idx % ROUTE_COLORS.length],
                          weight: 3,
                          opacity: 0.35,
                          dashArray: "6 6",
                        }}
                        eventHandlers={{ click: () => setSelectedIdx(idx) }}
                      />
                    )
                  )}
                  {selectedRoute && (
                    <Polyline
                      positions={selectedRoute.geometry}
                      pathOptions={{
                        color: ROUTE_COLORS[selectedIdx % ROUTE_COLORS.length],
                        weight: 6,
                        opacity: 0.95,
                      }}
                    />
                  )}

                  {selectedRoute && <FitBoundsToRoute geometry={selectedRoute.geometry} />}
                </>
              )}
            </MapContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
