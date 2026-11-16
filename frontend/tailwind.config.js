/** @type {import('tailwindcss').Config} */
// DeepCrop tokens. Light, airy greenhouse-dashboard world: pale grey-green canvas, near-white
// cards, near-black ink, leaf green as fill/marks only, mint for positive state fields.
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: '#E8EBE5',      // page ground
        shell: '#DFE3DC',       // inset wells, pill tracks
        card: '#FAFBF8',        // card surface
        tile: '#F1F3EE',        // tiles inside cards
        ink: '#141814',         // headings, numerals, primary button
        muted: '#596158',       // secondary text (5.6:1 on card)
        faint: '#7C847B',       // tertiary text, units (3.6:1, large text only)
        line: '#D3D8CF',        // hairlines
        leaf: {
          DEFAULT: '#22C55E',   // marks, fills, gauge arcs
          bright: '#3EE06F',
          deep: '#13662F',      // green text on light (7.2:1)
          mint: '#DCF5E3',      // positive state fields
          wash: '#EEF9F1',
        },
        warn: { DEFAULT: '#B26B00', field: '#FBEFD9' },
        alert: { DEFAULT: '#C2322B', field: '#FBE3E1' },
      },
      fontFamily: {
        sans: ['"Hanken Grotesk Variable"', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        card: '16px',
        tile: '12px',
      },
      boxShadow: {
        card: '0 1px 2px rgba(20, 24, 20, 0.04), 0 8px 24px -12px rgba(20, 24, 20, 0.12)',
        lift: '0 2px 4px rgba(20, 24, 20, 0.06), 0 16px 32px -16px rgba(20, 24, 20, 0.22)',
      },
      letterSpacing: {
        display: '-0.03em',
      },
    },
  },
  plugins: [],
}
