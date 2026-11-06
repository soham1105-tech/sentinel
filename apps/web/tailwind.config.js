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
        muted: "#94A3B8",
      },
    },
  },
  plugins: [],
};
