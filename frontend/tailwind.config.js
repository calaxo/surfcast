/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0b1622',
        card: '#122232',
        card2: '#0e1b28',
        ink: '#e8f0f7',
        mut: '#8aa4bd',
        line: '#22384f',
        good: '#37d67a',
        ok: '#f6c945',
        bad: '#ff6b6b',
        accent: '#38bdf8',   // cyan océan (primaire)
        sunset: '#ff9f45',   // orange coucher de soleil (secondaire, cf. icône)
      },
      boxShadow: {
        card: '0 1px 0 0 rgba(255,255,255,.02) inset, 0 8px 24px -16px rgba(0,0,0,.6)',
      },
      fontFamily: {
        sans: ['system-ui', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['ui-monospace', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
