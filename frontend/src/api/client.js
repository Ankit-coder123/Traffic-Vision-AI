import axios from "axios";

const API_BASE_URL = "http://localhost:8000";

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
  signup: (name, email, password, role = "operator") =>
    client.post("/auth/signup", { name, email, password, role }),
  me: () => client.get("/auth/me"),
};

export const trafficApi = {
  getLive: () => client.get("/traffic/live"),
  getZones: () => client.get("/traffic/zones"),
  getHistory: (zoneId) => client.get(`/traffic/history/${zoneId}`),
};

export default client;
