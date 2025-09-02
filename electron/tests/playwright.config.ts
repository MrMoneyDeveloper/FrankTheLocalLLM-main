import { PlaywrightTestConfig } from '@playwright/test';

const config: PlaywrightTestConfig = {
  testDir: './specs',
  timeout: 60_000,
  use: {
    headless: true,
  },
};

export default config;

