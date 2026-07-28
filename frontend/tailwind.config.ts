import type { Config } from 'tailwindcss'

// Dark minimalist visual contract (constitution Principle V):
// Zinc/Slate palette (canvas #09090b, surface #18181b), 10/12/14px type scale,
// weights 400/500/600, tracking-wider, 1px translucent hairline borders.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#09090b',
        surface: '#18181b',
        hairline: 'rgba(255,255,255,0.05)',
      },
      fontSize: {
        // 10px uppercase micro-labels / 12px controls / 14px body+input
        micro: ['10px', { lineHeight: '14px' }],
        control: ['12px', { lineHeight: '16px' }],
        body: ['14px', { lineHeight: '20px' }],
      },
      letterSpacing: {
        wider: '0.05em',
      },
    },
  },
  plugins: [],
} satisfies Config
