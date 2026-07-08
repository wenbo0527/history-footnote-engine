import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8765',
        changeOrigin: true
      }
    }
  },
  build: {
    target: 'es2022',
    cssMinify: 'lightningcss',
    cssCodeSplit: true,           // CSS 拆包，按页面加载
    sourcemap: false,             // 生产不生成 sourcemap
    minify: 'esbuild',
    rollupOptions: {
      output: {
        // 拆包策略
        manualChunks: (id) => {
          if (id.includes('node_modules/svelte')) return 'svelte';
          if (id.includes('node_modules/marked')) return 'markdown';
          if (id.includes('node_modules/lucide-svelte')) return 'icons';
          if (id.includes('node_modules')) return 'vendor';
          if (id.includes('lib/components/design-system')) return 'design-system';
          if (id.includes('lib/components/game')) return 'game';
        }
      }
    }
  },
  esbuild: {
    legalComments: 'none',
    drop: ['console', 'debugger']  // 生产移除 console
  }
});
