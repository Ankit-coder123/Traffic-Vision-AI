import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AlertBell from "./AlertBell";

const NAV_LINKS = [
  { to: "/dashboard", label: "Live Monitoring", roles: ["admin", "operator", "user"] },
  { to: "/prediction", label: "Prediction", roles: ["admin", "operator", "user"] },
  { to: "/routes", label: "Routes", roles: ["admin", "operator", "user"] },
  { to: "/analytics", label: "Analytics", roles: ["admin", "operator", "user"] },
  { to: "/incidents", label: "Incidents", roles: ["admin", "operator"] },
];

const ROLE_BADGES = {
  admin: { label: "Admin", icon: "\u2726", className: "bg-signal-severe/10 text-signal-severe border-signal-severe/30" },
  operator: { label: "Operator", icon: "\u2699", className: "bg-accent/10 text-accent border-accent/30" },
  user: { label: "User", icon: "\u25CF", className: "bg-console-border/40 text-console-muted border-console-border" },
};

function RoleBadge({ role }) {
  const badge = ROLE_BADGES[role] || ROLE_BADGES.user;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wide border ${badge.className}`}
    >
      <span>{badge.icon}</span>
      {badge.label}
    </span>
  );
}

export default function NavBar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const visibleLinks = NAV_LINKS.filter((link) => link.roles.includes(user?.role));

  return (
    <header className="border-b border-console-border bg-console-panel">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <div>
            <h1 className="font-display font-bold text-lg text-console-text tracking-tight">
              TrafficVision <span className="text-accent">AI</span>
            </h1>
            <p className="text-console-muted text-xs font-mono mt-0.5 hidden sm:flex items-center gap-1.5">
              Operator console
              <span className="text-console-border">&middot;</span>
              <span className="inline-flex items-center gap-1 text-accent">
                <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                Bangalore
              </span>
            </p>
          </div>

          {/* Desktop nav -- hidden below md, replaced by the hamburger menu */}
          <nav className="hidden md:flex gap-1">
            {visibleLinks.map((link) => {
              const active = location.pathname === link.to;
              return (
                <Link
                  key={link.to}
                  to={link.to}
                  className={`px-3 py-1.5 rounded text-xs font-mono uppercase tracking-wide transition-colors ${
                    active
                      ? "bg-accent/10 text-accent border border-accent/30"
                      : "text-console-muted hover:text-console-text border border-transparent"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Desktop right side -- hidden below md */}
        <div className="hidden md:flex items-center gap-4">
          <AlertBell />
          <Link to="/profile" className="text-right group cursor-pointer">
            <div className="text-console-text text-sm font-body group-hover:text-accent transition-colors">
              {user?.name}
            </div>
            <div className="mt-0.5">
              <RoleBadge role={user?.role} />
            </div>
          </Link>
          <button
            onClick={logout}
            className="text-console-muted hover:text-console-text text-xs font-mono border border-console-border rounded px-3 py-1.5 hover:border-accent/50 transition-colors"
          >
            Sign out
          </button>
        </div>

        {/* Mobile right side: alert bell always visible + hamburger toggle */}
        <div className="flex md:hidden items-center gap-3">
          <AlertBell />
          <button
            onClick={() => setMobileOpen((v) => !v)}
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileOpen}
            className="text-console-text p-1.5 rounded border border-console-border hover:border-accent/50 transition-colors"
          >
            {mobileOpen ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M6 6l12 12M18 6l-12 12" strokeLinecap="round" />
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 7h16M4 12h16M4 17h16" strokeLinecap="round" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Mobile dropdown menu */}
      <div
        className={`md:hidden overflow-hidden transition-all duration-200 ease-out ${
          mobileOpen ? "max-h-96 border-t border-console-border" : "max-h-0"
        }`}
      >
        <nav className="flex flex-col px-4 py-3 gap-1">
          {visibleLinks.map((link) => {
            const active = location.pathname === link.to;
            return (
              <Link
                key={link.to}
                to={link.to}
                onClick={() => setMobileOpen(false)}
                className={`px-3 py-2 rounded text-sm font-mono uppercase tracking-wide transition-colors ${
                  active
                    ? "bg-accent/10 text-accent border border-accent/30"
                    : "text-console-muted hover:text-console-text hover:bg-console-bg/50 border border-transparent"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-console-border px-4 py-3 flex items-center justify-between">
          <Link
            to="/profile"
            onClick={() => setMobileOpen(false)}
            className="flex items-center gap-2 group"
          >
            <span className="text-console-text text-sm font-body group-hover:text-accent transition-colors">
              {user?.name}
            </span>
            <RoleBadge role={user?.role} />
          </Link>
          <button
            onClick={logout}
            className="text-console-muted hover:text-console-text text-xs font-mono border border-console-border rounded px-3 py-1.5 hover:border-accent/50 transition-colors"
          >
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}
