const LEVEL_CONFIG = {
  low: {
    label: "Flowing",
    dot: "bg-signal-low",
    badge: "bg-signal-low/10 text-signal-low border-signal-low/30",
  },
  medium: {
    label: "Moderate",
    dot: "bg-signal-medium",
    badge: "bg-signal-medium/10 text-signal-medium border-signal-medium/30",
  },
  high: {
    label: "Heavy",
    dot: "bg-signal-high",
    badge: "bg-signal-high/10 text-signal-high border-signal-high/30",
  },
  severe: {
    label: "Gridlock",
    dot: "bg-signal-severe",
    badge: "bg-signal-severe/10 text-signal-severe border-signal-severe/30",
  },
};

export default function ZoneCard({ zoneName, reading, index = 0 }) {
  const level = reading?.congestion_level || "low";
  const config = LEVEL_CONFIG[level] || LEVEL_CONFIG.low;

  return (
    <div
      className="bg-console-panel border border-console-border rounded-lg p-4 animate-fade-in transition-all duration-200 hover:-translate-y-0.5 hover:border-console-border/80 hover:shadow-lg hover:shadow-black/20"
      style={{ animationDelay: `${Math.min(index, 12) * 40}ms`, animationFillMode: "backwards" }}
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-display font-semibold text-console-text text-sm leading-tight pr-2">
          {zoneName}
        </h3>
        <span className={`w-2 h-2 rounded-full ${config.dot} live-pulse shrink-0 mt-1`} />
      </div>

      <div
        className={`inline-block px-2 py-0.5 rounded text-xs font-mono uppercase tracking-wide mb-4 border ${config.badge}`}
      >
        {config.label}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="text-console-muted text-[10px] font-mono uppercase tracking-wide mb-0.5">
            Vehicles
          </div>
          <div className="font-mono text-console-text text-xl font-medium tabular-nums">
            {reading?.vehicle_count ?? "—"}
          </div>
        </div>
        <div>
          <div className="text-console-muted text-[10px] font-mono uppercase tracking-wide mb-0.5">
            Avg speed
          </div>
          <div className="font-mono text-console-text text-xl font-medium tabular-nums">
            {reading?.avg_speed_kmph ?? "—"}
            <span className="text-console-muted text-xs ml-1">km/h</span>
          </div>
        </div>
      </div>

      {reading?.recorded_at && (
        <div className="text-console-muted text-[10px] font-mono mt-3 pt-3 border-t border-console-border">
          Updated {new Date(reading.recorded_at).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}
