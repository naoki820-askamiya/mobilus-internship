import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    // バックエンドAPIへのプロキシ設定
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'http://127.0.0.1:8000',
        ws: true,
        // WebSocket正常切断時のプロキシエラーのみ抑制（EPIPE/ECONNRESET）
        onProxyReqWs: (_proxyReq, _req, socket) => {
          socket.on('error', (err) => {
            if (err.code === 'EPIPE' || err.code === 'ECONNRESET') {
              // WebSocket切断時に発生する想定内のエラー。無視する。
              return;
            }
            console.error('[ws proxy] unexpected socket error:', err);
          });
        },
      },
    },
  },
});
