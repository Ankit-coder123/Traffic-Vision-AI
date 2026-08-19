/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        console: {
          bg: "#0B0F14",
          panel: "#121821",
          panel2: "#1A222D",
          border: "#232D3A",
          text: "#E4E9ED",
          muted: "#7C8A9A",
        },
        signal: {
          low: "#34D399",
          medium: "#FBBF24",
          high: "#FB923C",
          severe: "#F43F5E",
        },
        accent: "#22D3EE",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
        body: ["'Inter'", "sans-serif"],
      },
      keyframes: {
        // Page/section content settling in on mount -- small enough to read
        // as "smooth" rather than "slow" (the whole thing is done in 250ms).
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        // For popovers/dropdowns (AlertBell) -- scales in from just under
        // full size rather than sliding, since it's anchored to a trigger
        // button rather than filling a page.
        "fade-in-scale": {
          "0%": { opacity: "0", transform: "scale(0.97)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
      },
      animation: {
        "fade-in": "fade-in 250ms ease-out",
        "fade-in-scale": "fade-in-scale 150ms ease-out",
      },
    },
  },
  plugins: [],
};
