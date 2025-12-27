export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        // Premium warm palette - intimate & relationship-focused
        cream: {
          50: '#FEFDFB',
          100: '#FDF9F3',
          200: '#FAF3E8',
          300: '#F5EADB',
        },
        rose: {
          50: '#FFF5F5',
          100: '#FFE8E8',
          200: '#FECDD3',
          300: '#FDA4AF',
          400: '#FB7185',
          500: '#F43F5E',
          600: '#E11D48',
        },
        blush: {
          50: '#FDF2F4',
          100: '#FCE7EA',
          200: '#F9D0D9',
          300: '#F4A8B8',
          400: '#EC7A94',
          500: '#DC4E6F',
          600: '#C73E5C',
        },
        warmGray: {
          50: '#FAFAF9',
          100: '#F5F5F4',
          200: '#E7E5E4',
          300: '#D6D3D1',
          400: '#A8A29E',
          500: '#78716C',
          600: '#57534E',
          700: '#44403C',
          800: '#292524',
          900: '#1C1917',
        },
        peach: {
          100: '#FFF1EB',
          200: '#FFE4D9',
          300: '#FFD0BE',
          400: '#FFB399',
        },
        lavender: {
          100: '#F5F3FF',
          200: '#EDE9FE',
          300: '#DDD6FE',
          400: '#C4B5FD',
        },
        // Keep existing accent for compatibility
        accent: {
          DEFAULT: '#A78295',
          light: '#C4B0BB',
          lighter: '#E8DFE5',
        },
        text: {
          primary: '#1C1917',
          secondary: '#57534E',
          tertiary: '#78716C',
          muted: '#A8A29E',
        },
        border: {
          subtle: '#E7E5E4',
          light: '#D6D3D1',
          medium: '#A8A29E',
        },
      },
      boxShadow: {
        'soft': '0 1px 2px rgba(0, 0, 0, 0.04)',
        'subtle': '0 2px 8px rgba(0, 0, 0, 0.04)',
        'cozy': '0 4px 16px rgba(0, 0, 0, 0.06)',
        'lifted': '0 8px 32px rgba(0, 0, 0, 0.08)',
        'glow': '0 0 40px rgba(244, 63, 94, 0.15)',
        'glow-lg': '0 0 60px rgba(244, 63, 94, 0.2)',
        'inner-glow': 'inset 0 1px 0 rgba(255, 255, 255, 0.6)',
        'glass': '0 8px 32px rgba(0, 0, 0, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.4)',
      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
        '4xl': '2.5rem',
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },
      fontFamily: {
        sans: ['SF Pro Display', '-apple-system', 'BlinkMacSystemFont', 'Inter', 'Segoe UI', 'sans-serif'],
        display: ['SF Pro Display', '-apple-system', 'BlinkMacSystemFont', 'Inter', 'sans-serif'],
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
        'display-lg': ['3.5rem', { lineHeight: '1.1', letterSpacing: '-0.02em', fontWeight: '600' }],
        'display': ['2.5rem', { lineHeight: '1.2', letterSpacing: '-0.02em', fontWeight: '600' }],
        'display-sm': ['2rem', { lineHeight: '1.2', letterSpacing: '-0.01em', fontWeight: '600' }],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-warm': 'linear-gradient(135deg, #FDF2F4 0%, #FFF1EB 50%, #F5F3FF 100%)',
        'gradient-rose': 'linear-gradient(135deg, #FDA4AF 0%, #F472B6 100%)',
        'gradient-sunset': 'linear-gradient(135deg, #F43F5E 0%, #FB923C 100%)',
        'gradient-glass': 'linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.7) 100%)',
      },
      backdropBlur: {
        'xs': '2px',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'float-slow': 'float 8s ease-in-out infinite',
        'float-slower': 'float 10s ease-in-out infinite',
        'pulse-soft': 'pulse-soft 4s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'gradient': 'gradient 8s ease infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
        gradient: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
      },
    },
  },
  plugins: [],
}
