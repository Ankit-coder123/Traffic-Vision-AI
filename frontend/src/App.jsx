import { Suspense, lazy } from "react";
import { BrowserRouter, Routes as RouterRoutes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Signup from "./pages/Signup";

// Lazy-loaded: each of these becomes its own JS chunk, fetched only when
// the person actually navigates there, instead of all being bundled into
// the initial page load (which previously meant a login page visitor
// downloaded jsPDF, Leaflet, and Recharts before they'd even signed in).
// Login/Signup stay eager-loaded since they're the very first thing almost
// everyone sees.
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Prediction = lazy(() => import("./pages/Prediction"));
const Routes = lazy(() => import("./pages/Routes"));
const Incidents = lazy(() => import("./pages/Incidents"));
const Analytics = lazy(() => import("./pages/Analytics"));
const Profile = lazy(() => import("./pages/Profile"));

function PageLoadingFallback() {
  return (
    <div className="min-h-screen bg-console-bg flex items-center justify-center">
      <div className="flex items-center gap-3 text-console-muted font-mono text-sm">
        <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
        Loading...
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Suspense fallback={<PageLoadingFallback />}>
          <RouterRoutes>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/prediction"
              element={
                <ProtectedRoute>
                  <Prediction />
                </ProtectedRoute>
              }
            />
            <Route
              path="/routes"
              element={
                <ProtectedRoute>
                  <Routes />
                </ProtectedRoute>
              }
            />
            <Route
              path="/incidents"
              element={
                <ProtectedRoute>
                  <Incidents />
                </ProtectedRoute>
              }
            />
            <Route
              path="/analytics"
              element={
                <ProtectedRoute>
                  <Analytics />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <Profile />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </RouterRoutes>
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
}
