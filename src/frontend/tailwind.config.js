/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],

  theme: {
    extend: {
      // 🆕 v2.0：国风雅致设计令牌（从 tokens.css 同步）
      colors: {
        // 纸张
        paper: {
          DEFAULT: 'var(--color-paper)',
          aged: 'var(--color-paper-aged)',
          dark: 'var(--color-paper-dark)'
        },
        // 墨色
        ink: {
          DEFAULT: 'var(--color-ink)',
          mid: 'var(--color-ink-mid)',
          light: 'var(--color-ink-light)',
          faint: 'var(--color-ink-faint)'
        },
        // 主色
        bronze: {
          DEFAULT: 'var(--color-bronze)',
          dark: 'var(--color-bronze-dark)',
          light: 'var(--color-bronze-light)'
        },
        // 朱砂
        cinnabar: {
          DEFAULT: 'var(--color-cinnabar)',
          dark: 'var(--color-cinnabar-dark)',
          light: 'var(--color-cinnabar-light)'
        }
      },
      // 字体
      fontFamily: {
        display: ['var(--font-display)'],
        body: ['var(--font-body)'],
        numeric: ['var(--font-numeric)'],
        en: ['var(--font-en)']
      },
      // 字号（流体）
      fontSize: {
        body: 'var(--text-body-fluid)',
        title: 'var(--text-title-fluid)',
        hero: 'var(--text-hero-fluid)'
      },
      // 行高
      lineHeight: {
        relaxed: 'var(--leading-relaxed)',
        normal: 'var(--leading-normal)'
      },
      // 间距
      spacing: {
        fluid: 'var(--space-fluid-md)',
        'fluid-lg': 'var(--space-fluid-lg)'
      },
      // 时长
      transitionDuration: {
        quick: 'var(--duration-quick)',
        normal: 'var(--duration-normal)',
        slow: 'var(--duration-slow)',
        grand: 'var(--duration-grand)'
      },
      // 缓动
      transitionTimingFunction: {
        ink: 'var(--ease-ink)',
        brush: 'var(--ease-brush)',
        paper: 'var(--ease-paper)'
      }
    }
  },

  // 保留 Tailwind 的工具类
  plugins: []
};
