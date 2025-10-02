// Tailwind preset shared across apps in the monorepo.
// It resolves tailwind modules from the consumer app (cwd) to work when builds
// run from a subdirectory (e.g., apps/tenant or apps/admin on Render).

function resolveFromCwd(id) {
  try {
    return require(id)
  } catch (_) {
    const resolved = require.resolve(id, { paths: [process.cwd()] })
    return require(resolved)
  }
}

const defaultTheme = resolveFromCwd('tailwindcss/defaultTheme')
const plugin = resolveFromCwd('tailwindcss/plugin')

/** @type {import('tailwindcss').Config} */
module.exports = {
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a'
        }
      },
      borderRadius: {
        xl: '1.125rem',
        '2xl': '1.5rem',
        '3xl': '2rem'
      },
      fontFamily: {
        sans: ['Inter', ...defaultTheme.fontFamily.sans]
      },
      boxShadow: {
        brand: '0 20px 45px rgba(15, 23, 42, 0.08)'
      }
    }
  },
  plugins: [
    plugin(({ addVariant }) => {
      addVariant('hocus', ['&:hover', '&:focus-visible'])
    })
  ]
}

