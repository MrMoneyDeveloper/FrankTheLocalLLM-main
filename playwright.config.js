const { defineConfig } = require('@playwright/test');
const path = require('path');

module.exports = defineConfig({
  testDir: './tests/playwright',
  use: {
    baseURL: process.env.PW_BASE_URL || 'http://localhost:5173'
  },
  projects: [
    {
      name: 'browser',
      use: { browserName: 'chromium', headless: true }
    },
    {
      name: 'tauri',
      use: {
        browserName: 'chromium',
        headless: true,
        launchOptions: {
          args: ['--app=' + path.join(__dirname, 'app/index.html')]
        }
      }
    }
  ]
});
