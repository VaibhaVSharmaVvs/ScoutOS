/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        pitch: {
          900: "#0a1f14",
          800: "#0d2b1a",
          700: "#124025",
          600: "#166534",
          500: "#1d7a45",
          400: "#22c55e",
        },
        surface: {
          900: "#0b1120",
          800: "#111827",
          700: "#1f2937",
          600: "#374151",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
