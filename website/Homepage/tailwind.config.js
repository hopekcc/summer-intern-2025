/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html", // all HTML in Homepage/templates
    "./static/**/*.js",      // all JS in Homepage/static
    "./**/*.py"              // optional: if classes appear in Python strings
  ],
  theme: { extend: {} },
  plugins: [],
};
