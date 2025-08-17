const { test, expect } = require('@playwright/test');

// helper to mock login, note endpoints and qa response
async function setupRoutes(page) {
  await page.route('**/api/auth/login', route => {
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ access_token: 't', token_type: 'bearer' }) });
  });
  const notes = [];
  await page.route('**/api/entries', async route => {
    if (route.request().method() === 'POST') {
      const body = JSON.parse(route.request().postData());
      const note = { id: notes.length + 1, content: body.content, summary: null, summarized: false };
      notes.push(note);
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(note) });
    } else {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(notes) });
    }
  });
  await page.route('**/api/qa/stream', route => {
    route.fulfill({ status: 200, body: 'AI answer' });
  });
}

test('creates note and shows AI answer', async ({ page }) => {
  await setupRoutes(page);
  await page.goto('/');
  await page.getByRole('textbox').first().fill('bob');
  await page.getByRole('textbox').nth(1).fill('pw');
  await page.getByRole('button', { name: 'Login' }).click();
  await expect(page.getByText('Login successful!')).toBeVisible();

  await page.evaluate(() => fetch('/api/entries', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({content:'New note'})}));
  await page.reload();
  await expect(page.getByText('New note')).toBeVisible();

  await page.getByPlaceholder('Say hi').fill('hello');
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(page.getByText('AI answer')).toBeVisible();
});
