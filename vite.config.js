import { defineConfig } from 'vite';
import { Features } from 'lightningcss';
import {
  getComponentChunkLinks,
  getFontLinks,
  getLoaderScript,
} from '@porsche-design-system/components-js/partials';

export default defineConfig({
  server: {
    host: '127.0.0.1',
    port: Number(process.env.ELO_WEB_PORT || 5173),
    strictPort: true,
    proxy: Object.fromEntries(['/api', '/health'].map((path) => [path, {
      target: `http://127.0.0.1:${process.env.ELO_API_PORT || 8001}`,
      changeOrigin: true,
    }])),
  },
  // Keep the design system's native light-dark() color tokens intact.
  css: {
    transformer: 'lightningcss',
    lightningcss: {
      exclude: Features.LightDark,
    },
  },
  plugins: [
    {
      name: 'porsche-design-system',
      transformIndexHtml(html) {
        const preloads = [
          getFontLinks({ weights: ['regular', 'semi-bold', 'bold'] }),
          getComponentChunkLinks({ components: [
            'accordion', 'button', 'divider', 'heading', 'inline-notification',
            'input-date', 'input-text', 'link', 'link-pure', 'select',
            'spinner', 'tabs-bar', 'tag', 'text', 'text-list', 'textarea',
          ] }),
        ].join('');

        return html
          .replace('</head>', () => `${preloads}</head>`)
          .replace('</body>', () => `${getLoaderScript()}</body>`);
      },
    },
  ],
});
