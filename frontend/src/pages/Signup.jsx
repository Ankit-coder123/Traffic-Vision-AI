import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import GoogleSignInButton from "../components/GoogleSignInButton";

const STRENGTH_LEVELS = [
  { label: "Very Weak", color: "bg-signal-severe", text: "text-signal-severe" },
  { label: "Weak", color: "bg-signal-high", text: "text-signal-high" },
  { label: "Fair", color: "bg-signal-medium", text: "text-signal-medium" },
  { label: "Good", color: "bg-accent", text: "text-accent" },
  { label: "Strong", color: "bg-signal-low", text: "text-signal-low" },
];

function scorePasswordStrength(pw) {
  if (!pw) return 0;
  let score = 0;
  if (pw.length >= 6) score++;
  if (pw.length >= 10) score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return Math.min(score, 4);
}

export default function Signup() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState("user");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { signup } = useAuth();
  const navigate = useNavigate();
  const strengthScore = scorePasswordStrength(password);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    setSubmitting(true);
    try {
      await signup(name, email, password, role);
      navigate("/dashboard");
    } catch (err) {
      setError(
        err.response?.status === 400
          ? "An account with this email already exists. Try signing in instead."
          : "Couldn't reach the server. Check that the backend is running."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-console-bg flex items-center justify-center px-4">
      <div className="w-full max-w-sm animate-fade-in">
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
            Create your account &middot; Bangalore
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

          <div className="mb-4">
            <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
              Account Type
            </span>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setRole("user")}
                className={`px-3 py-2.5 rounded border text-xs font-mono uppercase tracking-wide transition-colors ${
                  role === "user"
                    ? "border-accent bg-accent/10 text-accent"
                    : "border-console-border text-console-muted hover:text-console-text"
                }`}
              >
                Public User
              </button>
              <button
                type="button"
                onClick={() => setRole("operator")}
                className={`px-3 py-2.5 rounded border text-xs font-mono uppercase tracking-wide transition-colors ${
                  role === "operator"
                    ? "border-accent bg-accent/10 text-accent"
                    : "border-console-border text-console-muted hover:text-console-text"
                }`}
              >
                Traffic Operator
              </button>
            </div>
            <p className="text-console-muted text-[10px] font-mono mt-1.5">
              {role === "user"
                ? "View live traffic, get congestion predictions, and find optimized routes."
                : "Same access as Public User, plus operational tooling for traffic staff."}
            </p>
          </div>

          <label className="block mb-4">
            <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
              Full Name
            </span>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Jane Doe"
              className="w-full bg-console-bg border border-console-border rounded px-3 py-2.5 text-console-text placeholder:text-console-muted/50 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent font-body text-sm"
            />
          </label>

          <label className="block mb-4">
            <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
              Email
            </span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@gmail.com"
              className="w-full bg-console-bg border border-console-border rounded px-3 py-2.5 text-console-text placeholder:text-console-muted/50 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent font-body text-sm"
            />
          </label>

          <label className="block mb-4">
            <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
              Password
            </span>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 6 characters"
              className="w-full bg-console-bg border border-console-border rounded px-3 py-2.5 text-console-text placeholder:text-console-muted/50 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent font-body text-sm"
            />
            {password.length > 0 && (
              <div className="mt-2">
                <div className="flex gap-1 mb-1">
                  {[0, 1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className={`h-1 flex-1 rounded-full transition-colors ${
                        i <= strengthScore
                          ? STRENGTH_LEVELS[strengthScore].color
                          : "bg-console-border"
                      }`}
                    />
                  ))}
                </div>
                <p className={`text-[10px] font-mono ${STRENGTH_LEVELS[strengthScore].text}`}>
                  {STRENGTH_LEVELS[strengthScore].label}
                  {strengthScore < 2 && " — try adding numbers, symbols, or mixed case"}
                </p>
              </div>
            )}
          </label>

          <label className="block mb-6">
            <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
              Confirm Password
            </span>
            <input
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
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
            {submitting ? "Creating account..." : "Create Account"}
          </button>
        </form>

        <GoogleSignInButton
          onError={setError}
          note="Google sign-in always creates a Public User account (upgrade to Traffic Operator later isn't self-service)."
        />

        <p className="text-center text-console-muted text-xs mt-5 font-body">
          Already have an account?{" "}
          <Link to="/login" className="text-accent hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
