export default {
  content: [
  './index.html',
  './src/**/*.{js,ts,jsx,tsx}'
],
  theme: {
    extend: {
      colors: {
        lavender: '#e6e6fa',
        blush: '#ffdddd',
        mint: '#d0f0e0',
        beige: '#f5f0e8',
      },
      boxShadow: {
        'soft': '0 4px 14px 0 rgba(0, 0, 0, 0.05)',
        'cozy': '0 6px 20px rgba(0, 0, 0, 0.08)',
      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
      },
    },
    fontFamily: {
      nunito: ['Nunito', 'sans-serif'],
    },
  },
  plugins: [],
}