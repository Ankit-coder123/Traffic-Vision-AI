// Generic pulsing placeholder block. Pages compose these into layouts that
// mirror their real content's shape (see ZoneCard/SummaryCard/incident row
// skeletons in Dashboard.jsx / Analytics.jsx / Incidents.jsx) so the skeleton
// doesn't jump/reflow once real data arrives.
export function Skeleton({ className = "" }) {
  return <div className={`animate-pulse bg-console-border/40 rounded ${className}`} />;
}
