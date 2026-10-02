/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // graphite surfaces
        base: "#101114",
        panel: "#17191d",
        raised: "#1e2025",
        line: "#2b2e35",
        // text
        ink: "#ebe9e4",
        mute: "#8d919b",
        // orange accent
        accent: { DEFAULT: "#f97316", soft: "#fb923c", deep: "#c2570c" },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
