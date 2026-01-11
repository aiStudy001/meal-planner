import { test, expect } from '@playwright/test';

/**
 * Phase 7 Screenshots - Documentation Screenshot Capture
 *
 * This test suite captures 8 screenshots (08-15) for Phase 7 features:
 * - 끼니 재생성 (Meal Regeneration)
 * - 대체 레시피 제안 (Alternative Recipes)
 * - LocalStorage 식단 관리 (Saved Meal Plans)
 *
 * Prerequisites:
 * - Backend server running on http://localhost:8000
 * - Frontend server running on http://localhost:5173
 * - ANTHROPIC_API_KEY and TAVILY_API_KEY configured
 */

test.describe('Phase 7 Screenshots', () => {
  // Generate a meal plan before each test
  test.beforeEach(async ({ page }) => {
    // Navigate to home page
    await page.goto('/');

    // Select test scenario (체중 감량 남성)
    await page.waitForSelector('select', { timeout: 10000 });
    await page.selectOption('select', '체중 감량 남성');

    // Click start button
    await page.click('button:has-text("시작하기")');

    // Wait for meal plan completion (up to 2 minutes)
    console.log('Waiting for meal plan generation...');
    await page.waitForSelector('text=식단이 완성되었습니다', { timeout: 120000 });
    console.log('Meal plan generated successfully');

    // Wait for initial render
    await page.waitForTimeout(1000);
  });

  /**
   * Screenshot 08: Export Buttons (PDF, JSON, Shopping List)
   */
  test('08-result-export-buttons', async ({ page }) => {
    console.log('Capturing screenshot 08: Export buttons');

    // Scroll to export buttons area
    await page.locator('button:has-text("PDF로 저장")').scrollIntoViewIfNeeded();

    // Wait for all buttons to be visible
    await expect(page.locator('button:has-text("PDF로 저장")')).toBeVisible();
    await expect(page.locator('button:has-text("JSON 저장")')).toBeVisible();
    await expect(page.locator('button:has-text("장보기 리스트")')).toBeVisible();

    // Capture screenshot
    await page.screenshot({
      path: 'screenshots/demo/08-result-export-buttons.png',
      fullPage: false,
    });

    console.log('Screenshot 08 captured successfully');
  });

  /**
   * Screenshot 09: Shopping List Modal
   */
  test('09-shopping-list-modal', async ({ page }) => {
    console.log('Capturing screenshot 09: Shopping list modal');

    // Click shopping list button
    await page.click('button:has-text("장보기 리스트")');

    // Wait for modal to appear
    await expect(page.locator('[role="dialog"]')).toBeVisible();
    await page.waitForTimeout(500); // Animation delay

    // Capture screenshot
    await page.screenshot({
      path: 'screenshots/demo/09-shopping-list-modal.png',
      fullPage: false,
    });

    console.log('Screenshot 09 captured successfully');

    // Close modal for next test
    await page.click('button:has-text("닫기")');
  });

  /**
   * Screenshot 10: Meal Card Actions (Regenerate & Alternative buttons)
   */
  test('10-meal-card-actions', async ({ page }) => {
    console.log('Capturing screenshot 10: Meal card actions');

    // Find first meal card
    const firstMealCard = page.locator('.meal-card').first();

    // Hover to show action buttons
    await firstMealCard.hover();
    await page.waitForTimeout(300); // Hover effect delay

    // Capture screenshot of just the meal card
    await firstMealCard.screenshot({
      path: 'screenshots/demo/10-meal-card-actions.png',
    });

    console.log('Screenshot 10 captured successfully');
  });

  /**
   * Screenshot 11: Regenerate Confirmation (2-click confirmation state)
   */
  test('11-regenerate-confirm', async ({ page }) => {
    console.log('Capturing screenshot 11: Regenerate confirmation');

    // Click regenerate button once
    const regenerateBtn = page.locator('.meal-card').first().locator('button:has-text("다시 생성")');
    await regenerateBtn.click();

    // Wait for confirmation state
    await page.waitForTimeout(200);
    await expect(page.locator('button:has-text("정말 다시 생성하시겠습니까?")')).toBeVisible();

    // Capture screenshot of meal card in confirmation state
    await page.locator('.meal-card').first().screenshot({
      path: 'screenshots/demo/11-regenerate-confirm.png',
    });

    console.log('Screenshot 11 captured successfully');
  });

  /**
   * Screenshot 12: Regenerate Progress (SSE streaming)
   */
  test('12-regenerate-progress', async ({ page }) => {
    console.log('Capturing screenshot 12: Regenerate progress');

    // Double-click to confirm regeneration
    const regenerateBtn = page.locator('.meal-card').first().locator('button:has-text("다시 생성")');
    await regenerateBtn.click();
    await page.waitForTimeout(100);
    await regenerateBtn.click(); // Second click to confirm

    // Wait for SSE streaming to start
    try {
      await page.waitForSelector('text=재생성 중', { timeout: 5000 });
      await page.waitForTimeout(500); // Capture during progress
    } catch (error) {
      console.log('Could not find "재생성 중" text, checking for loading state...');
      // Alternative: check for any loading state
      await page.waitForTimeout(1000);
    }

    // Capture screenshot
    await page.locator('.meal-card').first().screenshot({
      path: 'screenshots/demo/12-regenerate-progress.png',
    });

    console.log('Screenshot 12 captured successfully');
  });

  /**
   * Screenshot 13: Alternatives Modal (3 alternative recipes)
   */
  test('13-alternatives-modal', async ({ page }) => {
    console.log('Capturing screenshot 13: Alternatives modal');

    // Click alternatives button
    await page.locator('.meal-card').first().locator('button:has-text("비슷한 레시피")').click();

    // Wait for modal and data to load
    await page.waitForSelector('[role="dialog"]:has-text("대체 레시피")', { timeout: 10000 });
    await page.waitForTimeout(1000); // Wait for API response

    // Capture screenshot
    await page.screenshot({
      path: 'screenshots/demo/13-alternatives-modal.png',
      fullPage: false,
    });

    console.log('Screenshot 13 captured successfully');
  });

  /**
   * Screenshot 14: Saved Plans Button (Save & Load controls)
   */
  test('14-saved-plans-button', async ({ page }) => {
    console.log('Capturing screenshot 14: Saved plans button');

    // Scroll to save controls
    await page.locator('button:has-text("식단 저장")').scrollIntoViewIfNeeded();

    // Verify buttons are visible
    await expect(page.locator('button:has-text("💾 식단 저장")')).toBeVisible();
    await expect(page.locator('button:has-text("📂 저장된 식단")')).toBeVisible();

    // Capture screenshot of save controls area
    const saveButton = page.locator('button:has-text("식단 저장")').first();
    await saveButton.screenshot({
      path: 'screenshots/demo/14-saved-plans-button.png',
    });

    console.log('Screenshot 14 captured successfully');
  });

  /**
   * Screenshot 15: Saved Plans Modal (List with metadata)
   */
  test('15-saved-plans-modal', async ({ page }) => {
    console.log('Capturing screenshot 15: Saved plans modal');

    // Save current plan first
    await page.click('button:has-text("💾 식단 저장")');
    await page.waitForTimeout(500); // Wait for save operation

    // Open saved plans modal
    await page.click('button:has-text("📂 저장된 식단")');
    await page.waitForSelector('[role="dialog"]:has-text("저장된 식단")');
    await page.waitForTimeout(500); // Animation delay

    // Capture screenshot
    await page.screenshot({
      path: 'screenshots/demo/15-saved-plans-modal.png',
      fullPage: false,
    });

    console.log('Screenshot 15 captured successfully');
  });
});
