import { defineConfig } from '@playwright/test';
export default defineConfig({ testDir: './tests', expect: { timeout: 30000 }, use: { baseURL: 'http://127.0.0.1:8000', channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome' }, workers: 1 });
