import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import GoogleSignInButton from "../components/GoogleSignInButton";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(
        err.response?.status === 401
          ? "Incorrect email or password."
          : "Couldn't reach the server. Check that the backend is running."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-console-bg flex items-center justify-center px-4">
      <div className="w-full max-w-sm animate-fade-in">
        {/* Signature: terminal-style header with a live status readout */}
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-2 mb-3">
            <span className="w-2 h-2 rounded-full bg-signal-low live-pulse" />
            <span className="text-xs font-mono text-console-muted tracking-widest uppercase">
              System Online
            </span>
          </div>
          <h1 className="font-display font-bold text-3xl text-console-text tracking-tight">
            TrafficVision <span className="text-accent">AI</span>
          </h1>
          <p className="text-console-muted text-sm mt-1 font-body">
            Operator console access &middot; Bangalore
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-console-panel border border-console-border rounded-lg p-6"
        >
          {error && (
            <div className="mb-4 px-3 py-2 rounded bg-signal-severe/10 border border-signal-severe/30 text-signal-severe text-sm font-body">
              {error}
            </div>
          )}

          <label className="block mb-4">
            <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
              Email
            </span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="operator@trafficvision.ai"
              className="w-full bg-console-bg border border-console-border rounded px-3 py-2.5 text-console-text placeholder:text-console-muted/50 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent font-body text-sm"
            />
          </label>

          <label className="block mb-6">
            <span className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-mono text-console-muted uppercase tracking-wide">
                Password
              </span>
              <Link
                to="/forgot-password"
                className="text-xs text-accent hover:underline font-body normal-case"
              >
                Forgot password?
              </Link>
            </span>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-console-bg border border-console-border rounded px-3 py-2.5 text-console-text placeholder:text-console-muted/50 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent font-body text-sm"
            />
          </label>

          <button
            type="submit"
            disabled={submitting}
            className="w-full flex items-center justify-center gap-2 bg-accent text-console-bg font-display font-semibold rounded py-2.5 text-sm tracking-wide hover:bg-accent/90 active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100 disabled:cursor-not-allowed transition"
          >
            {submitting && (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
            )}
            {submitting ? "Authenticating..." : "Sign in"}
          </button>
        </form>

        <GoogleSignInButton onError={setError} />

        <p className="text-center text-console-muted text-xs mt-5 font-body">
          New here?{" "}
          <Link to="/signup" className="text-accent hover:underline">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
