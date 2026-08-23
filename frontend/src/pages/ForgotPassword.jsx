import { useState } from "react";
import { Link } from "react-router-dom";
import { authApi } from "../api/client";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      // Backend always returns the same generic message whether or not
      // the email is registered, by design -- so we don't need to (and
      // shouldn't) branch on the response here.
      await authApi.forgotPassword(email);
      setSubmitted(true);
    } catch (err) {
      setError("Couldn't reach the server. Check that the backend is running.");
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
          <p className="text-console-muted text-sm mt-1 font-body">Reset your password</p>
        </div>

        <div className="bg-console-panel border border-console-border rounded-lg p-6">
          {submitted ? (
            <div className="text-center py-2">
              <p className="text-console-text text-sm font-body mb-4">
                If an account exists for <span className="text-accent">{email}</span>, a
                password reset link has been sent. Check your inbox (and spam folder).
              </p>
              <Link to="/login" className="text-accent text-sm hover:underline">
                Back to sign in
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              {error && (
                <div className="mb-4 px-3 py-2 rounded bg-signal-severe/10 border border-signal-severe/30 text-signal-severe text-sm font-body">
                  {error}
                </div>
              )}

              <p className="text-console-muted text-sm font-body mb-4">
                Enter the email associated with your account and we'll send you a link to
                reset your password.
              </p>

              <label className="block mb-6">
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

              <button
                type="submit"
                disabled={submitting}
                className="w-full flex items-center justify-center gap-2 bg-accent text-console-bg font-display font-semibold rounded py-2.5 text-sm tracking-wide hover:bg-accent/90 active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100 disabled:cursor-not-allowed transition"
              >
                {submitting ? "Sending..." : "Send reset link"}
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
