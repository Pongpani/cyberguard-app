import {test, expect} from '@playwright/test';
test('scan, display real host, statistics and mobile layout', async ({page})=>{
  await page.goto('/');
  await page.getByRole('navigation',{name:'เมนูหลัก'}).getByRole('button',{name:'ตรวจสอบ',exact:true}).click();
  await expect(page.getByRole('heading',{name:'เช็กให้ชัวร์ ก่อนคลิกลิงก์'})).toBeVisible();
  await page.getByLabel('URL ที่ต้องการตรวจสอบ').fill('https://account.example@192.0.2.10/login');
  await page.getByRole('button',{name:'ตรวจสอบลิงก์',exact:true}).click();
  await expect(page.locator('.host')).toHaveText('192.0.2.10');
  await expect(page.locator('.score')).toContainText('55');
  await expect(page.getByText('บันทึกเฉพาะผลสรุปแล้ว')).toBeVisible();
  await page.screenshot({path:'test-results/desktop-result.png',fullPage:true});
  await page.getByRole('navigation').getByRole('button',{name:'สถิติ',exact:true}).click();
  await expect(page.getByRole('heading',{name:'สถิติการตรวจสอบ'})).toBeVisible();
  await expect(page.locator('.metric.all strong')).not.toHaveText('0 ครั้ง');
  await page.screenshot({path:'test-results/statistics.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.getByRole('navigation').getByRole('button',{name:'ตรวจสอบ',exact:true}).click();
  await expect(page.getByLabel('URL ที่ต้องการตรวจสอบ')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.screenshot({path:'test-results/mobile-result.png',fullPage:true});
});
test('invalid URL can be corrected',async({page})=>{
  await page.goto('/');
  await page.getByRole('navigation',{name:'เมนูหลัก'}).getByRole('button',{name:'ตรวจสอบ',exact:true}).click();
  await page.getByLabel('URL ที่ต้องการตรวจสอบ').fill('javascript:alert(1)');
  await page.getByRole('button',{name:'ตรวจสอบลิงก์',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('รูปแบบ URL ไม่ถูกต้อง');
  await page.getByLabel('URL ที่ต้องการตรวจสอบ').fill('example.com');
  await page.getByRole('button',{name:'ตรวจสอบลิงก์',exact:true}).click();
  await expect(page.locator('.host')).toHaveText('example.com');
  await expect(page.locator('.score')).toContainText('0');
});


