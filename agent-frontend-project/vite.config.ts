import vue from '@vitejs/plugin-vue'
import path from 'node:path'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // 加载对应模式下的环境变量（development / test / production）
  const env = loadEnv(mode, process.cwd(), '')

  // 后端代理目标地址：优先读取环境变量，未配置则回退到本地后端
  const proxyTarget = env.VITE_PROXY_TARGET || 'http://localhost:8000'

  return {
    plugins: [vue()],

    // 路径别名：@ 指向 src 目录
    resolve: {
      alias: {
        '@': path.resolve(import.meta.dirname, 'src'),
      },
    },

    // 本地开发服务器配置
    server: {
      host: '0.0.0.0',
      port: Number(env.VITE_PORT) || 5173,
      open: true,
      // 跨域代理：所有以 VITE_API_PREFIX 开头的请求转发到后端
      proxy: {
        [env.VITE_API_PREFIX || '/api']: {
          target: proxyTarget,
          changeOrigin: true,
          // 重写路径：移除请求前缀，避免后端重复接收 /api
          rewrite: (requestPath) =>
            requestPath.replace(new RegExp(`^${env.VITE_API_PREFIX || '/api'}`), ''),
        },
      },
    },

    // 构建配置
    build: {
      outDir: 'dist',
      sourcemap: mode !== 'production',
      chunkSizeWarningLimit: 1500,
      rollupOptions: {
        output: {
          // 静态资源分桶，便于缓存复用
          manualChunks: (id) => {
            if (id.includes('node_modules')) {
              if (id.includes('element-plus')) {
                return 'element-plus'
              }
              if (id.includes('@wangeditor')) {
                return 'wangeditor'
              }
              if (id.includes('vue')) {
                return 'vue'
              }
            }
          },
        },
      },
    },
  }
})
