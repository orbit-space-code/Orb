/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#1a1a1a',
        foreground: '#e0e0e0',
        accent: '#3b82f6',
        'phase-research': '#9333ea',
        'phase-planning': '#eab308',
        'phase-implementation': '#3b82f6',
        'phase-complete': '#22c55e',
        'status-active': '#22c55e',
        'status-paused': '#eab308',
        'status-failed': '#ef4444',
        'status-cancelled': '#6b7280',
      },
    },
  },
  plugins: [],
  darkMode: 'class',
}
