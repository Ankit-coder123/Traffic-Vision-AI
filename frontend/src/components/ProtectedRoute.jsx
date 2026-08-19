import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-console-bg">
        <div className="flex items-center gap-3 text-console-muted font-mono text-sm">
          <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
          Checking credentials...
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
