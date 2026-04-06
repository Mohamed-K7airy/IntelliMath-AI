import { defineConfig } from 'vite';
import { resolve } from 'path';
import react from '@vitejs/plugin-react';

export default defineConfig({
    plugins: [react()],
    server: {
        proxy: {
            '/solve_stream': {
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
                about: resolve(__dirname, 'about.html')
            }
        }
    }
});
