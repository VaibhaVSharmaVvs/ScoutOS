/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        pitch: {
          900: "#0a1f14",
          700: "#124025",
          500: "#1d7a45",
        },
      },
    },
  },
  plugins: [],
};
