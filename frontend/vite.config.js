import { defineConfig } from 'vite';
import { resolve } from 'path';
import react from '@vitejs/plugin-react';

export default defineConfig({
    plugins: [react()],
    server: {
        proxy: {
            // ✅ FIX (C-08): Added all backend endpoints for proper proxying
            '/solve_stream': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                secure: false,
            },
            '/solve': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                secure: false,
            },
            '/study': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                secure: false,
            },
            '/hints': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                secure: false,
            },
            '/health': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                secure: false,
            },
            '/ocr': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                secure: false,
            },
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                secure: false,
            }
        }
    },
    build: {
        rollupOptions: {
            input: {
                main: resolve(__dirname, 'index.html'),
                dashboard: resolve(__dirname, 'dashboard.html'),
                login: resolve(__dirname, 'login.html'),
                signup: resolve(__dirname, 'signup.html'),
                about: resolve(__dirname, 'about.html'),
                studyMode: resolve(__dirname, 'study-mode.html')
            }
        }
    }
});
