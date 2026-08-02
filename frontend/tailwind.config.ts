import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: {
          50: '#FDFCFB',
          100: '#FAF8F5',
          200: '#F4F0EA',
          300: '#E7E2D8',
          400: '#D6CFBF',
          500: '#C2B8A3',
          800: '#4A463D',
          900: '#1C1917',
        },
        charcoal: {
          50: '#F6F6F6',
          100: '#E7E7E7',
          400: '#737373',
          700: '#404040',
          800: '#262626',
          900: '#171717',
          950: '#0A0A0A',
        },
        matilda: {
          red: '#B91C1C',
          'red-light': '#FEF2F2',
          'red-border': '#FCA5A5',
          'red-muted': '#991B1B',
          accent: '#9A3412',
        }
      },
      fontFamily: {
        serif: ['Georgia', 'Cambria', '"Times New Roman"', 'Times', 'serif'],
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        'paper': '0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02)',
        'paper-lg': '0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.03)',
      }
    },
  },
  plugins: [],
};
export default config;
