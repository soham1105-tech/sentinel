/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0B1220",
        panel: "#111B2E",
        line: "#223048",
        pass: "#22C55E",
        fail: "#EF4444",
        accent: "#6EE7B7",
        muted: "#A7B4C7",
      },
      boxShadow: {
        panel: "0 28px 80px rgba(0,0,0,0.28)",
        "pass-glow": "0 0 46px rgba(34,197,94,0.16)",
        "accent-glow": "0 0 34px rgba(110,231,183,0.35)",
      },
    },
  },
  plugins: [],
};
