/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // MULEFLAGGER — Premium Financial Intelligence palette.
        bg: "#F5F6F8",
        surface: "#FFFFFF",
        surface2: "#F0F2F5",
        rowAlt: "#FAFBFC",
        border: "#E2E6ED",
        primary: "#1B2A4A",
        accent: "#2D7A9C",
        critical: "#C53030",
        high: "#B7791F",
        medium: "#997B2F",
        low: "#2B6C3F",
        textPrimary: "#1A202C",
        textSecondary: "#5A6B7F",
        textMuted: "#8E99A8",
      },
      fontFamily: {
        display: ['"IBM Plex Sans"', "sans-serif"],
        body: ['"Inter"', "sans-serif"],
        mono: ['"IBM Plex Mono"', "monospace"],
      },
      borderRadius: {
        none: "0",
        sm: "4px",
        DEFAULT: "8px",
        md: "12px",
        lg: "16px",
        xl: "20px",
      },
      boxShadow: {
        sm: "0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)",
        md: "0 4px 12px rgba(0,0,0,0.07), 0 1px 4px rgba(0,0,0,0.04)",
        lg: "0 10px 30px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04)",
        xl: "0 20px 50px rgba(0,0,0,0.10)",
      },
      maxWidth: {
        content: "1440px",
      },
      keyframes: {
        pulseCritical: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.6" },
        },
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        pulseCritical: "pulseCritical 2s ease-in-out infinite",
        fadeIn: "fadeIn 200ms ease-out",
      },
    },
  },
  plugins: [],
};
