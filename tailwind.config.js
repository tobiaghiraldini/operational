/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["DM Sans", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Plus Jakarta Sans", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        soft: "0 12px 40px rgba(15, 23, 42, 0.08)",
      },
    },
  },
  plugins: [],
};
