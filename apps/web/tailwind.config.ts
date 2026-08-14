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
        gold: {
          50: "#FFFDF0",
          100: "#FFF9C4",
          200: "#FFF380",
          300: "#FFE83D",
          400: "#FFDC0A",
          500: "#D4AF37", // Metallic gold
          600: "#B38F22",
          700: "#8C6E14",
          800: "#664F0A",
          900: "#403104",
        },
        burgundy: {
          50: "#FDF2F4",
          100: "#FADCE1",
          200: "#F5B8C3",
          300: "#EE8AA0",
          400: "#E35478",
          500: "#800020", // Deep Burgundy
          600: "#6B001B",
          700: "#540015",
          800: "#3D000F",
          900: "#29000A",
        },
      },
      fontFamily: {
        serif: ["Georgia", "Cambria", "Times New Roman", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      animation: {
        "fade-in": "fadeIn 0.5s ease-out forwards",
        "pulse-glow": "pulseGlow 3s infinite ease-in-out",
      },
      keyframes: {
        fadeIn: {
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        pulseGlow: {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "0.8" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
