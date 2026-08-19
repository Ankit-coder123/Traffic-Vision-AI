import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import NavBar from "../components/NavBar";

const ROLE_LABELS = {
  admin: "Admin",
  operator: "Traffic Operator",
  user: "Public User",
};

export default function Profile() {
  const { user, updateProfile } = useAuth();

  const [name, setName] = useState(user?.name || "");
  const [nameSubmitting, setNameSubmitting] = useState(false);
  const [nameMessage, setNameMessage] = useState("");
  const [nameError, setNameError] = useState("");

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordSubmitting, setPasswordSubmitting] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState("");
  const [passwordError, setPasswordError] = useState("");

  const handleNameSubmit = async (e) => {
    e.preventDefault();
    setNameError("");
    setNameMessage("");
    const trimmed = name.trim();
    if (!trimmed) {
      setNameError("Name cannot be empty.");
      return;
    }
    if (trimmed === user?.name) {
      return;
    }
    setNameSubmitting(true);
    try {
      await updateProfile({ name: trimmed });
      setNameMessage("Name updated.");
    } catch (err) {
      setNameError(err.response?.data?.detail ? String(err.response.data.detail) : "Failed to update name.");
    } finally {
      setNameSubmitting(false);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setPasswordError("");
    setPasswordMessage("");
    if (!currentPassword || !newPassword) {
      setPasswordError("Both current and new password are required.");
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("New password and confirmation don't match.");
      return;
    }
    setPasswordSubmitting(true);
    try {
      await updateProfile({ current_password: currentPassword, new_password: newPassword });
      setPasswordMessage("Password changed successfully.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setPasswordError(err.response?.data?.detail ? String(err.response.data.detail) : "Failed to change password.");
    } finally {
      setPasswordSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-console-bg">
      <NavBar />
      <div className="max-w-2xl mx-auto px-6 py-10 animate-fade-in">
        <h1 className="text-2xl font-display font-bold text-console-text mb-1">Profile</h1>
        <p className="text-console-muted text-sm font-body mb-8">Manage your account details.</p>

        {/* Account info (read-only) */}
        <div className="bg-console-panel border border-console-border rounded-lg p-6 mb-6">
          <h2 className="text-console-text font-display font-semibold text-sm uppercase tracking-wide mb-4">
            Account
          </h2>
          <div className="space-y-3 text-sm font-body">
            <div className="flex justify-between">
              <span className="text-console-muted">Email</span>
              <span className="text-console-text">{user?.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-console-muted">Role</span>
              <span className="text-console-text">{ROLE_LABELS[user?.role] || user?.role}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-console-muted">Member since</span>
              <span className="text-console-text">
                {user?.created_at ? new Date(user.created_at).toLocaleDateString() : "—"}
              </span>
            </div>
          </div>
          <p className="text-console-muted text-xs font-mono mt-4">
            Email can't be changed here — it's your login identifier.
          </p>
        </div>

        {/* Edit name */}
        <form
          onSubmit={handleNameSubmit}
          className="bg-console-panel border border-console-border rounded-lg p-6 mb-6"
        >
          <h2 className="text-console-text font-display font-semibold text-sm uppercase tracking-wide mb-4">
            Display Name
          </h2>
          <label className="block text-console-muted text-xs font-mono uppercase tracking-wide mb-1.5">
            Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-console-bg border border-console-border rounded px-3 py-2 text-sm text-console-text font-body focus:outline-none focus:border-accent/50"
          />
          {nameError && <p className="text-signal-severe text-xs font-mono mt-2">{nameError}</p>}
          {nameMessage && <p className="text-accent text-xs font-mono mt-2">{nameMessage}</p>}
          <button
            type="submit"
            disabled={nameSubmitting}
            className="mt-4 bg-accent text-console-bg font-display font-semibold rounded px-4 py-2 text-sm tracking-wide hover:bg-accent/90 active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100 disabled:cursor-not-allowed transition"
          >
            {nameSubmitting ? "Saving..." : "Save Name"}
          </button>
        </form>

        {/* Change password */}
        <form
          onSubmit={handlePasswordSubmit}
          className="bg-console-panel border border-console-border rounded-lg p-6"
        >
          <h2 className="text-console-text font-display font-semibold text-sm uppercase tracking-wide mb-4">
            Change Password
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-console-muted text-xs font-mono uppercase tracking-wide mb-1.5">
                Current Password
              </label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full bg-console-bg border border-console-border rounded px-3 py-2 text-sm text-console-text font-body focus:outline-none focus:border-accent/50"
              />
            </div>
            <div>
              <label className="block text-console-muted text-xs font-mono uppercase tracking-wide mb-1.5">
                New Password
              </label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full bg-console-bg border border-console-border rounded px-3 py-2 text-sm text-console-text font-body focus:outline-none focus:border-accent/50"
              />
              <p className="text-console-muted text-[10px] font-mono mt-1">At least 8 characters.</p>
            </div>
            <div>
              <label className="block text-console-muted text-xs font-mono uppercase tracking-wide mb-1.5">
                Confirm New Password
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full bg-console-bg border border-console-border rounded px-3 py-2 text-sm text-console-text font-body focus:outline-none focus:border-accent/50"
              />
            </div>
          </div>
          {passwordError && <p className="text-signal-severe text-xs font-mono mt-3">{passwordError}</p>}
          {passwordMessage && <p className="text-accent text-xs font-mono mt-3">{passwordMessage}</p>}
          <button
            type="submit"
            disabled={passwordSubmitting}
            className="mt-4 bg-accent text-console-bg font-display font-semibold rounded px-4 py-2 text-sm tracking-wide hover:bg-accent/90 active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100 disabled:cursor-not-allowed transition"
          >
            {passwordSubmitting ? "Changing..." : "Change Password"}
          </button>
        </form>
      </div>
    </div>
  );
}
