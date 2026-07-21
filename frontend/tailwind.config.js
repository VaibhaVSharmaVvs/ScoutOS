/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "var(--canvas)",
        surface: {
          DEFAULT: "var(--surface-1)",
          raised: "var(--surface-2)",
          overlay: "var(--surface-3)",
        },
        input: "var(--input)",
        accent: {
          DEFAULT: "rgb(var(--accent) / <alpha-value>)",
          ink: "var(--accent-ink)",
          soft: "var(--accent-soft)",
        },
        ink: {
          DEFAULT: "var(--ink)",
          2: "var(--ink-2)",
          3: "var(--ink-3)",
          muted: "var(--ink-muted)",
        },
        positive: "rgb(var(--positive) / <alpha-value>)",
        warning: "rgb(var(--warning) / <alpha-value>)",
        danger: "rgb(var(--danger) / <alpha-value>)",
      },
      borderColor: {
        DEFAULT: "var(--line)",
        line: "var(--line)",
        strong: "var(--line-strong)",
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
      },
      fontFamily: {
        sans: ["Geist", "Geist Fallback", "system-ui", "sans-serif"],
        mono: ["Geist Mono", "ui-monospace", "monospace"],
      },
      fontSize: {
        // 14px base, ~1.25 ratio, rounded
        caption: ["11px", { lineHeight: "14px" }],
        sm: ["13px", { lineHeight: "18px" }],
        base: ["14px", { lineHeight: "20px" }],
        h4: ["16px", { lineHeight: "22px" }],
        h3: ["18px", { lineHeight: "24px" }],
        h2: ["22px", { lineHeight: "28px" }],
        h1: ["28px", { lineHeight: "32px" }],
        display: ["44px", { lineHeight: "44px", letterSpacing: "-0.03em" }],
      },
      transitionTimingFunction: {
        out: "cubic-bezier(0.23, 1, 0.32, 1)",
      },
    },
  },
  plugins: [],
};
