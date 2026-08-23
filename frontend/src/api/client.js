import axios from "axios";

// Falls back to localhost for local/Docker dev -- set VITE_API_BASE_URL at
// build time to point this at a deployed backend (e.g. Render).
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const client = axios.create({
  baseURL: API_BASE_URL,
});

// Attach the JWT to every outgoing request, if we have one
client.interceptors.request.use((config) => {
  const token = localStorage.getItem("tv_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// If the token is invalid/expired, boot the user back to login
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("tv_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: (email, password) => {
    // backend expects OAuth2 form data with 'username' field
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    return client.post("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },
  signup: (name, email, password, role = "user") =>
    client.post("/auth/signup", { name, email, password, role }),
  googleLogin: (credential) => client.post("/auth/google", { credential }),
  forgotPassword: (email) => client.post("/auth/forgot-password", { email }),
  resetPassword: (token, newPassword) =>
    client.post("/auth/reset-password", { token, new_password: newPassword }),
  me: () => client.get("/auth/me"),
  updateProfile: (payload) => client.patch("/auth/me", payload),
};

export const trafficApi = {
  getLive: () => client.get("/traffic/live"),
  getZones: () => client.get("/traffic/zones"),
  getHistory: (zoneId) => client.get(`/traffic/history/${zoneId}`),
};

export const predictionApi = {
  predictCongestion: (payload) => client.post("/predict/congestion", payload),
  getReports: (limit = 20) => client.get(`/predict/reports?limit=${limit}`),
};

export const routesApi = {
  optimize: (payload) => client.post("/routes/optimize", payload),
  saveRoute: (payload) => client.post("/routes/saved", payload),
  getSavedRoutes: () => client.get("/routes/saved"),
  deleteSavedRoute: (id) => client.delete(`/routes/saved/${id}`),
};

export const incidentsApi = {
  report: (payload) => client.post("/incidents", payload),
  list: (activeOnly = true) => client.get(`/incidents?active_only=${activeOnly}`),
  resolve: (id) => client.patch(`/incidents/${id}/resolve`, { is_resolved: true }),
};

export const analyticsApi = {
  getSummary: () => client.get("/analytics/summary"),
  getHeatmap: () => client.get("/analytics/heatmap"),
  getTrends: (hours = 24, zoneId = null) =>
    client.get(`/analytics/trends?hours=${hours}${zoneId ? `&zone_id=${zoneId}` : ""}`),
  getRecommendations: () => client.get("/analytics/recommendations"),
  dismissRecommendation: (zoneId, minutes = 30) =>
    client.post(`/analytics/recommendations/${zoneId}/dismiss?minutes=${minutes}`),
  getRoadPerformance: (hours = 24) => client.get(`/analytics/road-performance?hours=${hours}`),
  getPeakHours: (zoneId = null, days = 30) =>
    client.get(`/analytics/peak-hours?days=${days}${zoneId ? `&zone_id=${zoneId}` : ""}`),
  getRoadConditions: () => client.get("/analytics/road-conditions"),
};

export default client;
