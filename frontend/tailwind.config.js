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
    },
  },
  plugins: [],
};
