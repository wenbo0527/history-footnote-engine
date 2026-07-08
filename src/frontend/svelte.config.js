import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({
      pages: 'build',
      assets: 'build',
      fallback: 'index.html',   // SPA 模式
      precompress: false,
      strict: false
    }),
    // 开发期允许访问 Python 后端
    csrf: {
      checkOrigin: true
    }
  },
  compilerOptions: {
    runes: true   // 启用 Svelte 5 runes
  }
};

export default config;
