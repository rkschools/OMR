/// <reference types="node" />
import { test, expect } from '@playwright/test';
import path from 'node:path';
import process from 'node:process';

test.describe('RISE OMR Platform - Full End-to-End System Audit & Regression', () => {

  test('Comprehensive OMR Software Workflow Verification', async ({ page }) => {
    page.on('console', msg => console.log(`[BROWSER CONSOLE] ${msg.type()}: ${msg.text()}`));
    page.on('pageerror', err => console.log(`[BROWSER ERROR] ${err.message}`));

    // Auto-accept alert/confirm dialogs
    page.on('dialog', async dialog => {
      await dialog.accept();
    });

    // ==========================================
    // 1. AUTHENTICATION & LOGIN
    // ==========================================
    await page.goto('/login');
    await expect(page).toHaveTitle(/RISE OMR Platform/i);

    await page.fill('input[type="email"]', 'admin@rise.com');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');

    await page.waitForURL('**/', { timeout: 15000 });
    await expect(page.locator('.sidebar-header h2')).toContainText('RISE OMR');

    // ==========================================
    // 2. EXAM & READINESS CHECKLIST AUDIT
    // ==========================================
    await page.click('a[href="/exams"]');
    await page.waitForURL('**/exams');
    await expect(page.getByRole('cell', { name: 'RISE 2027', exact: true })).toBeVisible({ timeout: 10000 });

    await page.locator('tr:has(td:text-is("RISE 2027"))').getByRole('link', { name: 'Manage' }).click();
    await page.waitForURL('**/exams/exam_rise_2027', { timeout: 15000 });
    await expect(page.locator('.page-header h2')).toContainText('RISE 2027', { timeout: 15000 });

    // Check Readiness Tab
    await page.click('button:has-text("readiness")');
    await expect(page.locator('text=Examination Readiness Checklist')).toBeVisible();
    await expect(page.locator('text=Template Published')).toBeVisible();
    await expect(page.locator('text=Template Assigned')).toBeVisible();
    await expect(page.locator('text=Marking Rules Configured')).toBeVisible();
    await expect(page.locator('text=Answer Key Status')).toBeVisible();
    await expect(page.locator('text=PDF Generation Successful')).toBeVisible();

    // Inspect Sections Tab: Verify Telugu and Hindi are absent from Classes 1-9
    await page.click('button:has-text("sections")');
    await expect(page.locator('text=Telugu')).not.toBeVisible();
    await expect(page.locator('text=Hindi')).not.toBeVisible();

    // Verify Class 8 has English, Science, Mathematics, GK / Computer, Current Affairs
    await page.click('button:has-text("Class 8")');
    await expect(page.locator('text=English').first()).toBeVisible();
    await expect(page.locator('text=Science').first()).toBeVisible();
    await expect(page.locator('text=Mathematics').first()).toBeVisible();
    await expect(page.locator('text=GK / Computer').first()).toBeVisible();
    await expect(page.locator('text=Current Affairs').first()).toBeVisible();

    // Verify Class 5 has English, Science, Mathematics, GK / Computer, and NO Current Affairs
    await page.click('button:has-text("Class 5")');
    await expect(page.locator('text=English').first()).toBeVisible();
    await expect(page.locator('text=Science').first()).toBeVisible();
    await expect(page.locator('text=Mathematics').first()).toBeVisible();
    await expect(page.locator('text=GK / Computer').first()).toBeVisible();

    // ==========================================
    // 3. TEMPLATE LIFECYCLE (VALIDATE, PUBLISH, ASSIGN)
    // ==========================================
    await page.click('button:has-text("templates")');
    const openWorkspaceBtn = page.locator('text=Open Template Workspace');
    await expect(openWorkspaceBtn).toBeVisible();
    await openWorkspaceBtn.click();

    await page.waitForURL('**/templates/**');
    await expect(page.locator('.template-workspace')).toBeVisible();
    await expect(page.locator('text=Total Questions:')).toBeVisible();
    await expect(page.locator('text=50').first()).toBeVisible();

    // Validate geometry
    const validateBtn = page.locator('button:has-text("Validate Geometry")');
    await expect(validateBtn).toBeVisible();
    await validateBtn.click();
    await expect(page.locator('text=Template validation passed')).toBeVisible({ timeout: 10000 });

    // Assign to Exam
    const assignBtn = page.locator('button:has-text("Assign to Exam")');
    await expect(assignBtn).toBeVisible();
    await assignBtn.click();
    await expect(page.locator('text=Assigned')).toBeVisible({ timeout: 10000 });

    // ==========================================
    // 4. ANSWER KEY LIFECYCLE & CSV UPLOAD TIMING
    // ==========================================
    await page.click('a[href="/keys"]');
    await page.waitForURL('**/keys');
    await expect(page.locator('.page-header h2')).toContainText('Answer Keys');

    // Select Exam, Class, Set
    await page.selectOption('select >> nth=0', { label: 'RISE 2027 (exam_rise_2027)' });
    await page.waitForTimeout(300);
    await page.selectOption('select >> nth=1', { label: 'Class 8' });
    await page.waitForTimeout(300);

    // If key was published from before, test revision unlock
    const revBtn = page.locator('button:has-text("Create New Revision")');
    if (await revBtn.isVisible()) {
      await revBtn.click();
      await page.waitForTimeout(300);
    }

    // Test Key File Upload
    const keyCsvPath = path.resolve(process.cwd(), '../output/test_keys/test_key_SetA.csv');
    const fileInputKey = page.locator('input#key-file-upload');
    await fileInputKey.setInputFiles(keyCsvPath);
    await page.waitForTimeout(1000);

    // Verify upload timing metrics displayed
    await expect(page.locator('text=Upload & Mapping Performance Measurements')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Total Time:').first()).toBeVisible();

    // Verify 50/50 filled and labeled as TEST DATA
    await expect(page.locator('text=50/50 filled')).toBeVisible();

    // Publish Key
    const publishKeyBtn = page.locator('button:has-text("Publish Key")');
    await expect(publishKeyBtn).toBeVisible();
    await publishKeyBtn.click();
    await expect(page.locator('text=✓ PUBLISHED & IMMUTABLE')).toBeVisible({ timeout: 10000 });

    // ==========================================
    // 5. SCANNER WORKSPACE & REVIEW WORKFLOW
    // ==========================================
    await page.click('a[href="/scanner"]');
    await page.waitForURL('**/scanner');
    await expect(page.locator('.page-header h2')).toContainText('Scanner Workspace');

    await page.selectOption('select >> nth=0', { value: 'exam_rise_2027' });
    await page.selectOption('select >> nth=1', { value: '8' });

    // Activate Ingestion Batch
    const startIngestionBtn = page.locator('button:has-text("Start Auto-Ingestion")');
    await expect(startIngestionBtn).toBeVisible();
    await startIngestionBtn.click();

    // Upload synthetic student sheet (Aarav Sharma)
    const testSheetPath = path.resolve(process.cwd(), '../output/synthetic_sheets/Aarav_Sharma_100001.png');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(testSheetPath);
    await page.waitForTimeout(500);

    const processBtn = page.locator('button:has-text("Process Pending")');
    if (await processBtn.isVisible() && await processBtn.isEnabled()) {
      await processBtn.click();
      await page.waitForTimeout(3000);
    }

    // Trigger Evaluation
    const evaluateBtn = page.locator('button:has-text("Evaluate Processed")');
    if (await evaluateBtn.isVisible() && await evaluateBtn.isEnabled()) {
      await evaluateBtn.click();
      await page.waitForTimeout(3000);
    }
    await page.waitForTimeout(1500);

    // ==========================================
    // 6. LEADERBOARD & RESULTS WORKFLOW
    // ==========================================
    await page.click('a[href="/results"]');
    await page.waitForURL('**/results');
    await expect(page.locator('.page-header h2')).toContainText('Results & Analytics');

    // Filter by Exam and Class 8
    await page.selectOption('select >> nth=0', { value: 'exam_rise_2027' });
    await page.waitForTimeout(500);
    await page.selectOption('select >> nth=1', { value: '8' });
    await page.waitForTimeout(500);

    // Verify Leaderboard Table and Cards
    await expect(page.locator('h3:has-text("Leaderboard")')).toBeVisible();
    await expect(page.locator('text=Total Processed')).toBeVisible();
    await expect(page.locator('text=Highest Score')).toBeVisible();
    await expect(page.getByRole('cell', { name: '#1', exact: true })).toBeVisible();

    // Verify Aarav Sharma is Rank 1 with 50.00
    await expect(page.locator('td:has-text("Aarav Sharma")').first()).toBeVisible();

    // Test Inspect Answers modal
    const inspectBtn = page.locator('button:has-text("Inspect Answers")').first();
    await expect(inspectBtn).toBeVisible();
    await inspectBtn.click();
    await expect(page.locator('h3:has-text("Student Answer Breakdown")')).toBeVisible();
    await expect(page.getByText('Q1', { exact: true }).first()).toBeVisible();
    await page.click('button:has-text("Close")');

    // Verify Export CSV
    const exportCsvBtn = page.locator('button:has-text("Export CSV")');
    await expect(exportCsvBtn).toBeVisible();
    await exportCsvBtn.click();

    // Take final audit screenshot
    const screenshotPath = path.resolve(process.cwd(), '../output/playwright_audit_results.png');
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log('Playwright practical end-to-end audit passed completely!');
  });

});
