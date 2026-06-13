/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Exact MULEFLAGGER analyst palette.
        bg: "#050D1A",
        surface: "#0D1F35",
        surface2: "#112840",
        rowAlt: "#0A1828",
        border: "#1E3A5F",
        primary: "#1976D2",
        accent: "#00D4FF",
        critical: "#FF3B30",
        high: "#FF9500",
        medium: "#FFCC00",
        low: "#34C759",
        textPrimary: "#F0F6FF",
        textSecondary: "#7A9CC0",
        textMuted: "#3D6080",
      },
      fontFamily: {
        display: ['"Space Grotesk"', "sans-serif"],
        body: ['"Inter"', "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
      borderRadius: {
        none: "0",
        sm: "2px",
        DEFAULT: "4px",
        md: "6px",
      },
      maxWidth: {
        content: "1440px",
      },
      keyframes: {
        pulseCritical: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.45" },
        },
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        pulseCritical: "pulseCritical 1.6s ease-in-out infinite",
        fadeIn: "fadeIn 200ms ease-out",
      },
    },
  },
  plugins: [],
};
