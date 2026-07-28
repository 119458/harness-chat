import type { Config } from 'tailwindcss'

// Dark minimalist visual contract (constitution Principle V):
// 12/14/16px type scale (10px reserved for sidebar group titles + status/
// progress badges), weights 400/500/600, tracking-wider. Colors are semantic
// tokens backed by CSS variables defined in src/styles/index.css, so the
// light/dark theme flips automatically via the `dark` class on <html>.
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: 'rgb(var(--canvas-rgb) / <alpha-value>)',
        surface: 'rgb(var(--surface-rgb) / <alpha-value>)',
        hairline: 'var(--hairline)',
        fg: 'rgb(var(--fg-rgb) / <alpha-value>)',
        'fg-muted': 'rgb(var(--fg-muted-rgb) / <alpha-value>)',
        'fg-subtle': 'rgb(var(--fg-subtle-rgb) / <alpha-value>)',
        'fg-faint': 'rgb(var(--fg-faint-rgb) / <alpha-value>)',
      },
      fontSize: {
        // 10px uppercase micro-labels (sidebar group titles + status badges) /
        // 12px controls / 14px body+input / 16px emphasis (final answer)
        micro: ['10px', { lineHeight: '14px' }],
        control: ['12px', { lineHeight: '16px' }],
        body: ['14px', { lineHeight: '20px' }],
        emphasis: ['16px', { lineHeight: '24px' }],
      },
      letterSpacing: {
        wider: '0.05em',
      },
    },
  },
  plugins: [],
} satisfies Config
