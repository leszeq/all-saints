import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ivory: "#F7F3EA",
        parchment: "#EFE8DA",
        charcoal: "#24211E",
        gold: {
          50: "#FBF8EF", 100: "#F3EBD8", 200: "#E4D4AD", 300: "#D2B977", 400: "#B99750",
          500: "#A8843D", 600: "#88672E", 700: "#694C24", 800: "#4A351C", 900: "#2E2116",
        },
        burgundy: {
          50: "#FAF3F5", 100: "#F4E3E8", 200: "#E7C1CB", 300: "#D394A5", 400: "#B95F78",
          500: "#6B2033", 600: "#591A2A", 700: "#4B1725", 800: "#3A111C", 900: "#270B12",
        },
      },
      fontFamily: {
        serif: ["Literata", "Iowan Old Style", "Palatino Linotype", "Book Antiqua", "Georgia", "serif"],
        sans: ["Geist", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: { editorial: "0 18px 50px -32px rgba(36, 33, 30, 0.35)" },
      animation: { "fade-in": "fadeIn 0.45s ease-out forwards" },
      keyframes: {
        fadeIn: { from: { opacity: "0", transform: "translateY(8px)" }, to: { opacity: "1", transform: "translateY(0)" } },
      },
    },
  },
  plugins: [],
};

export default config;
