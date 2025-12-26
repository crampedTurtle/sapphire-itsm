/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        sapphire: {
          primary: '#0A2540',
          secondary: '#0d3252',
        },
      },
    },
  },
  plugins: [],
}

