import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // FPL brand palette
        fpl: {
          purple: "#37003c",
          purpleDeep: "#240029",
          pink: "#e90052",
          cyan: "#04f5ff",
          green: "#00ff87",
          red: "#c8102e", // Liverpool accent
        },
        ink: {
          900: "#0a0912",
          800: "#12101c",
          700: "#1b1830",
          600: "#241f3f",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 40px -10px rgba(233,0,82,0.45)",
        glowCyan: "0 0 40px -12px rgba(4,245,255,0.4)",
      },
    },
  },
  plugins: [],
};
export default config;
