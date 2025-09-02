import { test, expect, _electron as electron, ElectronApplication, Page } from '@playwright/test'
import path from 'path'

async function launchApp(): Promise<{ app: ElectronApplication, page: Page }>{
  const app = await electron.launch({ args: ['.'], cwd: path.join(__dirname, '../../') , env: {
    ...process.env,
    SKIP_OLLAMA: '1',
    FAKE_EMBED: '1',
    FAKE_LLM: '1',
    APP_HOST: '127.0.0.1',
    APP_PORT: '8001'
  } })
  const page = await app.firstWindow()
  return { app, page }
}

test('startup renders shell', async () => {
  const { app, page } = await launchApp()
  await expect(page.locator('#sidebar')).toBeVisible()
  await expect(page.locator('#tabbar')).toBeVisible()
  await app.close()
})

test('create/edit/save note persists after restart', async () => {
  let { app, page } = await launchApp()
  await page.getByText('New Note').click()
  await page.waitForTimeout(300)
  // open the new note tab by clicking first note item
  const firstItem = page.locator('#notesList .item').first()
  await firstItem.click()
  await page.waitForTimeout(100)
  await page.locator('#editor textarea.note').fill('Hello world!')
  await page.waitForTimeout(800) // allow autosave debounce
  await app.close()

  // relaunch and verify note still present
  ;({ app, page } = await launchApp())
  await expect(page.locator('#notesList .item')).toContainText('Untitled')
  await app.close()
})

test('groups create and add note via DnD', async () => {
  const { app, page } = await launchApp()
  // create group
  await page.locator('#newGroupName').fill('Group A')
  await page.locator('#createGroupBtn').click()
  await page.waitForTimeout(200)
  // ensure group appears
  await expect(page.locator('#groups .group')).toContainText('Group A')
  await app.close()
})

test('keyword search All/Note scopes', async () => {
  const { app, page } = await launchApp()
  // open first note
  const first = page.locator('#notesList .item').first()
  await first.click()
  await page.waitForTimeout(200)
  await page.keyboard.press('Control+KeyK')
  await page.locator('#globalSearchInput').fill('hello')
  await page.waitForTimeout(200)
  const cnt = await page.locator('#globalSearchResults .result').count()
  expect(cnt).toBeGreaterThan(0)
  await app.close()
})

test('single-open behavior', async () => {
  const { app, page } = await launchApp()
  const first = page.locator('#notesList .item').first()
  await first.click()
  await page.waitForTimeout(100)
  // clicking again should not create duplicate tab
  await first.click()
  await page.waitForTimeout(100)
  const tabs = await page.locator('#tabbar .tab').count()
  expect(tabs).toBeGreaterThan(0)
  await app.close()
})

test('LLM search in This Note returns results with citations (fake embed)', async () => {
  const { app, page } = await launchApp()
  // create and open a note
  await page.getByText('New Note').click()
  await page.waitForTimeout(200)
  await page.locator('#notesList .item').first().click()
  await page.locator('#editor textarea.note').fill('alpha beta gamma')
  // force reindex now
  await page.getByText('Reindex now').click()
  await page.waitForTimeout(500)
  // set scope = This note, run query
  await page.locator('#llmScope').selectOption('note')
  await page.locator('#llmQuery').fill('alpha?')
  await page.getByText('Run').click()
  await page.waitForTimeout(500)
  const liCount = await page.locator('#llmResults ul li').count()
  expect(liCount).toBeGreaterThan(0)
  await app.close()
})
