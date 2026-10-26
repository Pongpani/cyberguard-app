import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  use: {baseURL: process.env.TEST_BASE_URL || 'http://127.0.0.1:8001', browserName: 'chromium', channel: 'msedge'},
  workers: 1,
});

