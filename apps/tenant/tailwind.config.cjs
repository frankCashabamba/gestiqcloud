const preset = require('../packages/ui/tailwind.preset.cjs')

/** @type {import('tailwindcss').Config} */
module.exports = {
  presets: [preset],
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
    '../packages/ui/src/**/*.{js,ts,jsx,tsx}',
    '../packages/shared/src/**/*.{js,ts,jsx,tsx}'
  ],
  theme: {
    extend: {
      maxWidth: {
        '6xl': '72rem'
      }
    }
  },
  safelist: [
    {
      pattern: /bg-(?:emerald|rose|amber|blue|slate|neutral)-(?:50|100|500|600|700)/
    },
    {
      pattern: /text-(?:emerald|rose|amber|blue|slate|neutral)-(?:500|600|700|800)/
    }
  ]
}
