export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        // Refined neutral palette
        primary: {
          DEFAULT: '#FAFAF9',
          dark: '#F5F5F4',
        },
        secondary: '#F5F5F4',
        accent: {
          DEFAULT: '#A78295',
          light: '#C4B0BB',
          lighter: '#E8DFE5',
        },
        text: {
          primary: '#2C2C2C',
          secondary: '#6B6B6B',
          tertiary: '#8E8E8E',
        },
        border: {
          subtle: '#E4E4E7',
          light: '#D4D4D8',
          medium: '#A1A1AA',
        },
        surface: {
          elevated: '#FFFFFF',
          hover: '#F5F5F4',
        },
      },
      boxShadow: {
        'soft': '0 1px 2px rgba(0, 0, 0, 0.05)',
        'subtle': '0 1px 3px rgba(0, 0, 0, 0.08)',
        'cozy': '0 4px 8px rgba(0, 0, 0, 0.08)',
        'lifted': '0 8px 16px rgba(0, 0, 0, 0.1)',
      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
    },
  },
  plugins: [],
}