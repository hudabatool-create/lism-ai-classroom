import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Sampled from the Liwa International School logo mark (public/logo.png).
        brand: {
          50: "#f2fbfe",
          100: "#e6f8fd",
          200: "#bfedfb",
          300: "#99e1f8",
          400: "#4dcbf2",
          500: "#00b5ed",
          600: "#009ac9",
          700: "#007fa6",
          800: "#006482",
          900: "#00485f",
        },
      },
    },
  },
  plugins: [],
};

export default config;
