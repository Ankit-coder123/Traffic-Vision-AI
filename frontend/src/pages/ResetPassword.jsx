import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { authApi } from "../api/client";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const navigate = useNavigate();

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }

    setSubmitting(true);
    try {
      await authApi.resetPassword(token, newPassword);
      navigate("/login", { state: { resetSuccess: true } });
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "This reset link is invalid or has expired. Please request a new one."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-console-bg flex items-center justify-center px-4">
      <div className="w-full max-w-sm animate-fade-in">
        <div className="mb-8 text-center">
          <h1 className="font-display font-bold text-3xl text-console-text tracking-tight">
            TrafficVision <span className="text-accent">AI</span>
          </h1>
          <p className="text-console-muted text-sm mt-1 font-body">Choose a new password</p>
        </div>

        <div className="bg-console-panel border border-console-border rounded-lg p-6">
          {!token ? (
            <div className="text-center py-2">
              <p className="text-signal-severe text-sm font-body mb-4">
                This reset link is missing its token. Please use the link from your email,
                or request a new one.
              </p>
              <Link to="/forgot-password" className="text-accent text-sm hover:underline">
                Request a new link
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              {error && (
                <div className="mb-4 px-3 py-2 rounded bg-signal-severe/10 border border-signal-severe/30 text-signal-severe text-sm font-body">
                  {error}
                </div>
              )}

              <label className="block mb-4">
                <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
                  New password
                </span>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-console-bg border border-console-border rounded px-3 py-2.5 text-console-text placeholder:text-console-muted/50 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent font-body text-sm"
                />
              </label>

              <label className="block mb-6">
                <span className="block text-xs font-mono text-console-muted uppercase tracking-wide mb-1.5">
                  Confirm new password
                </span>
                <input
                  type="password"
                  required
                  minLength={8}
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
                {submitting ? "Resetting..." : "Reset password"}
              </button>
            </form>
          )}
        </div>

        <p className="text-center text-console-muted text-xs mt-5 font-body">
          <Link to="/login" className="text-accent hover:underline">
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
