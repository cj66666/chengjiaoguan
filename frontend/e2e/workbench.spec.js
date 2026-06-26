/**
 * [INPUT]: 依赖 @playwright/test、Vite 工作台、FastAPI /api/v1/demo 与配置 API
 * [OUTPUT]: 对外提供工作台浏览器 E2E，验证 Demo Seed、客户/报价、审批发送、通知/设置、设计稿导航页、密集列表、价格规则版本/更新、渠道凭据轮换与横向溢出
 * [POS]: frontend/e2e 的桌面/移动主链路测试，覆盖人工烟测最容易遗漏的 UI 到 API 接缝
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */

import { expect, test } from "@playwright/test";

const API_BASE_URL = process.env.E2E_API_BASE_URL || "";
const RUN_SELLER_OFFSET = (Date.now() % 100000) * 10;

test("workbench demo catalog flow", async ({ page }, testInfo) => {
  const sellerId = sellerIdFor(testInfo, 9100);

  await page.goto("/");
  await page.getByLabel("Seller", { exact: true }).fill(sellerId);
  await page.getByRole("button", { name: "Demo Seed" }).click();
  await expect(page.getByText("已生成 Demo 主链路数据")).toBeVisible();

  await page.getByRole("button", { name: "产品", exact: true }).click();
  await expect(page.getByRole("heading", { name: "价格规则列表" })).toBeVisible();

  await page.getByTestId("pricing-form-submit").click();
  await expect(page.getByText("价格规则已创建")).toBeVisible();

  const versionButton = page.locator('button[data-testid^="pricing-rule-"][data-testid$="-versions"]').first();
  await expect(versionButton).toBeVisible();
  const versionTestId = await versionButton.getAttribute("data-testid");
  const ruleId = versionTestId?.match(/^pricing-rule-(\d+)-versions$/)?.[1];
  expect(ruleId).toBeTruthy();

  await versionButton.click();
  await expect(page.getByText("pricing_rule_created")).toBeVisible();

  const editForm = page.getByTestId(`pricing-rule-${ruleId}-edit`);
  await editForm.locator('input[name="floor_price"]').fill("3.05");
  await page.getByTestId(`pricing-rule-${ruleId}-edit-submit`).click();
  await expect(page.getByText("价格规则已更新")).toBeVisible();

  await page.getByTestId(`pricing-rule-${ruleId}-versions`).click();
  await expect(page.getByText("pricing_rule_updated")).toBeVisible();
  await expect(page.getByText("floor 3.05 · currency USD", { exact: true })).toBeVisible();

  await page.getByTestId("channel-form-submit").click();
  await expect(page.getByText("渠道已创建")).toBeVisible();

  const currentCredentialRow = page.locator(".approval-row", { hasText: "key current" }).first();
  await expect(currentCredentialRow).toBeVisible();
  await currentCredentialRow.locator('button[data-testid^="channel-"][data-testid$="-rotate"]').click();
  await expect(page.getByText("渠道凭据已轮换")).toBeVisible();
  await expect(page.locator(".approval-row", { hasText: "key current" }).first()).toBeVisible();
  await expect(page).toHaveNoHorizontalOverflow();
});

test("workbench customer approval flow", async ({ page }, testInfo) => {
  const sellerId = sellerIdFor(testInfo, 9200);

  await page.goto("/");
  await page.getByLabel("Seller", { exact: true }).fill(sellerId);
  await page.getByRole("button", { name: "Demo Seed" }).click();
  await expect(page.getByText("已生成 Demo 主链路数据")).toBeVisible();

  await page.getByRole("button", { name: "客户", exact: true }).click();
  const customerOpen = page.locator('button[data-testid^="customer-"][data-testid$="-open"]').first();
  await expect(customerOpen).toBeVisible();
  await customerOpen.click();
  await expect(page.getByText("客户档案已加载")).toBeVisible();
  await expect(page.getByRole("heading", { name: "客户档案抽屉" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "客户活动" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "报价详情" })).toBeVisible();

  await page.getByRole("button", { name: "产品", exact: true }).click();
  await expect(page.getByText("6 个 SKU")).toBeVisible();
  await expect(page.getByRole("heading", { name: "价格规则列表" })).toBeVisible();
  await expect(page.locator(".profile")).not.toBeVisible();
  await expect(page.locator(".banner")).not.toBeVisible();
  await page.getByRole("button", { name: "客户", exact: true }).click();
  await expect(page.getByText("选择一个客户查看询盘、会话、报价与跟进。")).toBeVisible();
  await expect(page.getByRole("heading", { name: "客户活动" })).not.toBeVisible();

  await page.getByRole("button", { name: "看板", exact: true }).click();
  await page.getByTestId("metric-pending-handoffs").click();
  await expect(page.getByRole("heading", { name: "人工审批队列" })).toBeVisible();
  const approveButton = page.locator('button[data-testid^="approval-"][data-testid$="-approve"]').first();
  await expect(approveButton).toBeVisible();
  await approveButton.click();
  await expect(page.getByText("审批已执行，消息已进入投递边界")).toBeVisible();
  await expect(page).toHaveNoHorizontalOverflow();
});

test("workbench dashboard metric navigation flow", async ({ page }, testInfo) => {
  const sellerId = sellerIdFor(testInfo, 9250);

  await page.goto("/");
  await page.getByLabel("Seller", { exact: true }).fill(sellerId);
  await page.getByRole("button", { name: "Demo Seed" }).click();
  await expect(page.getByText("已生成 Demo 主链路数据")).toBeVisible();

  await page.getByTestId("metric-today-inquiries").click();
  await expect(page.locator(".split")).toBeVisible();
  await expect(page.getByTestId("inbox-workbench")).toBeVisible();
  await expect(page.getByText("已暂停自动发送 · 待你确认")).toBeVisible();
  await expect(page.getByText("AI 对话摘要")).toBeVisible();

  await page.getByRole("button", { name: "看板", exact: true }).click();
  await page.getByTestId("metric-pending-handoffs").click();
  await expect(page.locator('button[data-testid^="approval-"][data-testid$="-approve"]').first()).toBeVisible();

  await page.getByRole("button", { name: "看板", exact: true }).click();
  await page.getByTestId("metric-auto-handle-rate").click();
  await expect(page.locator(".analytics-page")).toBeVisible();

  await page.getByRole("button", { name: "看板", exact: true }).click();
  await page.getByTestId("metric-conversion").click();
  await expect(page.locator(".analytics-page")).toBeVisible();
  await expect(page).toHaveNoHorizontalOverflow();
});

test("workbench inbox guardrail actions stay above composer in short viewport", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop", "desktop short viewport regression");
  const sellerId = sellerIdFor(testInfo, 9260);

  await page.setViewportSize({ width: 1280, height: 760 });
  await page.goto("/");
  await page.getByLabel("Seller", { exact: true }).fill(sellerId);
  await Promise.all([
    page.waitForResponse((response) => response.url().includes("/api/v1/demo/seed") && response.ok()),
    page.getByRole("button", { name: "Demo Seed" }).click(),
  ]);
  await page.waitForLoadState("networkidle");

  await page.getByTestId("metric-today-inquiries").click();
  await expect(page.getByTestId("inbox-workbench")).toBeVisible();
  await expect(page.locator(".guardrail-actions")).toBeVisible();
  await expect(page.locator(".composer-bar")).toBeVisible();

  const boxes = await page.evaluate(() => ({
    actions: document.querySelector(".guardrail-actions")?.getBoundingClientRect().toJSON(),
    composer: document.querySelector(".composer-bar")?.getBoundingClientRect().toJSON(),
    thread: document.querySelector(".inbox-thread")?.getBoundingClientRect().toJSON(),
  }));

  expect(boxes.actions.bottom).toBeLessThanOrEqual(boxes.thread.bottom);
  expect(boxes.actions.bottom).toBeLessThanOrEqual(boxes.composer.top);
  await expect(page).toHaveNoHorizontalOverflow();
});

test("workbench inbox takeover flow works without pending approval", async ({ page, request }, testInfo) => {
  const sellerId = sellerIdFor(testInfo, 9270);
  const seeded = await seedSingleInquiry(request, sellerId, "takeover-free");

  await page.goto("/");
  await page.getByLabel("Seller", { exact: true }).fill(sellerId);
  await page.getByTestId("metric-today-inquiries").click();
  await expect(page.getByTestId("inbox-workbench")).toBeVisible();
  await page.getByTestId(`inquiry-${seeded.inquiry_id}-select`).click();

  const takeoverButton = page.locator(".inbox-actions button").nth(1);
  await expect(takeoverButton).toBeEnabled();
  await takeoverButton.click();
  await expect(takeoverButton).toBeDisabled();
  await expect(page.locator(".composer-input input")).toBeEnabled();

  await page.locator(".composer-input input").fill("Manual takeover reply.");
  await page.locator(".composer-input button").click();
  await expect(page.getByText("Manual takeover reply.")).toBeVisible();
  await expect(page).toHaveNoHorizontalOverflow();
});

test("workbench settings notification flow", async ({ page }, testInfo) => {
  const sellerId = sellerIdFor(testInfo, 9300);

  await page.goto("/");
  await page.getByLabel("Seller", { exact: true }).fill(sellerId);
  await page.getByRole("button", { name: "Demo Seed" }).click();
  await expect(page.getByText("已生成 Demo 主链路数据")).toBeVisible();

  await page.getByRole("button", { name: "语言", exact: true }).click();
  await expect(page.locator(".topbar-title")).toContainText("设置");
  await page.getByRole("button", { name: "看板", exact: true }).click();
  await page.getByRole("button", { name: "转人工通知", exact: true }).click();
  await expect(page.locator(".topbar-title")).toContainText("设置");

  await page.getByRole("button", { name: "设置", exact: true }).click();
  await expect(page.getByRole("heading", { name: "生产就绪" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "通知与调度" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "外部通道" })).toBeVisible();

  const settingsForm = page.getByTestId("settings-form");
  await expect(settingsForm).toBeVisible();
  await settingsForm.locator('input[name="name"]').fill(`E2E Exporter ${sellerId}`);
  await settingsForm.locator('input[name="phone"]').fill("+1-555-0100");
  await settingsForm.locator('input[name="large_order_approval_threshold"]').fill("12000");
  await page.getByTestId("settings-form-submit").click();
  await expect(page.getByText("设置已保存")).toBeVisible();

  const channelForm = page.getByTestId("settings-channel-form");
  await expect(channelForm).toBeVisible();
  await channelForm.locator('input[name="name"]').fill(`E2E Sales Inbox ${sellerId}`);
  await channelForm.locator('input[name="imap_host"]').fill("imap.example.com");
  await channelForm.locator('input[name="smtp_host"]').fill("smtp.example.com");
  await channelForm.locator('input[name="username"]').fill("sales@example.com");
  await channelForm.locator('input[name="password"]').fill("secret");
  await page.getByTestId("settings-channel-form-submit").click();
  await expect(page.getByText("渠道已创建")).toBeVisible();
  await expect(page.getByText(`E2E Sales Inbox ${sellerId}`)).toBeVisible();

  await page.route("**/api/v1/channels/*/poll-email?limit=5", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ channel_account_id: 1, fetched: 0, ingested: 0, duplicates: 0, items: [] }),
    });
  });
  await page.locator('button[data-testid^="channel-"][data-testid$="-poll"]').first().click();
  await expect(page.getByText("邮箱轮询已执行")).toBeVisible();

  const testDeliveryForm = page.locator('form[data-testid^="channel-"][data-testid$="-test-delivery"]').first();
  await expect(testDeliveryForm).toBeVisible();
  await testDeliveryForm.locator('input[name="to"]').fill("buyer@example.com");
  await testDeliveryForm.locator('input[name="body"]').fill("Closer dry-run test.");
  await testDeliveryForm.locator('button[type="submit"]').click();
  await expect(page.getByText("通道测试投递已生成")).toBeVisible();

  const archiveButton = page.locator('button[data-testid^="notification-"][data-testid$="-archive"]').first();
  await expect(archiveButton).toBeVisible();
  await archiveButton.click();
  await expect(page.getByText("通知状态已更新")).toBeVisible();

  await page.getByRole("button", { name: "运行调度入口", exact: true }).click();
  await expect(page.getByText("Workers 已运行")).toBeVisible();
  await expect(page).toHaveNoHorizontalOverflow();
});

test("workbench design navigation flow", async ({ page }, testInfo) => {
  const sellerId = sellerIdFor(testInfo, 9350);

  await page.goto("/");
  await page.getByLabel("Seller", { exact: true }).fill(sellerId);
  await page.getByRole("button", { name: "Demo Seed" }).click();
  await expect(page.getByText("已生成 Demo 主链路数据")).toBeVisible();

  await page.getByRole("button", { name: "报价规则", exact: true }).click();
  await expect(page.locator(".rules-page").getByRole("heading", { name: "报价规则" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "基础定价" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "报价预览" })).toBeVisible();
  await expect(page).toHaveNoHorizontalOverflow();

  await page.getByRole("button", { name: "数据看板", exact: true }).click();
  await expect(page.locator(".analytics-page").getByRole("heading", { name: "数据看板" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "转化漏斗" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "近 30 天趋势" })).toBeVisible();
  await expect(page).toHaveNoHorizontalOverflow();

  await page.getByRole("button", { name: "移动端", exact: true }).click();
  await expect(page.getByRole("heading", { name: "移动端 · 轻量接管" })).toBeVisible();
  await expect(page.getByText("推送提醒")).toBeVisible();
  await expect(page.getByRole("button", { name: "一键接管", exact: true })).toBeVisible();
  await expect(page).toHaveNoHorizontalOverflow();
});

test("workbench dense list flow", async ({ page, request }, testInfo) => {
  const sellerId = sellerIdFor(testInfo, 9400);

  await seedDenseInquiries(request, sellerId, 24);
  await page.goto("/");
  await page.getByLabel("Seller", { exact: true }).fill(sellerId);

  await page.getByRole("button", { name: "收件箱", exact: true }).click();
  const inquiryPanel = panelByTitle(page, "询盘收件箱");
  await expect(inquiryPanel.locator(".row")).toHaveCount(20);
  await expect(inquiryPanel.getByText("Dense Buyer 23")).toBeVisible();
  await expect(inquiryPanel.locator(".rows")).toHaveVerticalScroll();
  await expect(page).toHaveNoHorizontalOverflow();

  await page.getByRole("button", { name: "客户", exact: true }).click();
  const customerPanel = panelByTitle(page, "客户列表");
  await expect(customerPanel.locator(".row")).toHaveCount(20);
  await expect(customerPanel.getByText("Dense Buyer 23")).toBeVisible();
  await expect(customerPanel.locator(".rows")).toHaveVerticalScroll();
  await expect(page).toHaveNoHorizontalOverflow();
});

function sellerIdFor(testInfo, desktopBase) {
  return String(desktopBase + RUN_SELLER_OFFSET + (testInfo.project.name === "mobile" ? 1 : 0));
}

async function seedDenseInquiries(request, sellerId, count) {
  const headers = { Authorization: `Bearer seller:${sellerId}` };
  await expect(await request.post(apiUrl("/api/v1/demo/seed"), { headers })).toBeOK();
  for (let index = 0; index < count; index += 1) {
    const quantity = 2000 + index * 137;
    const response = await request.post(apiUrl("/api/v1/webhooks/site_form"), {
      headers,
      data: {
        channel: "site_form",
        channel_message_id: `dense-${sellerId}-${index}`,
        from: {
          name: `Dense Buyer ${index}`,
          company: `Dense Buyer ${index} International Procurement Consortium With Very Long Legal Name`,
          country: index % 2 === 0 ? "US" : "Germany",
          email: `dense-${sellerId}-${index}@example.com`,
        },
        content: `Need ${quantity} LED desk lamps shipped to US with private label packaging, spare parts, carton marks, inspection terms, and a long commercial note ${index}.`,
        language: "en",
        attachments: [],
        received_at: new Date(Date.UTC(2026, 5, 1, 0, index)).toISOString(),
      },
    });
    await expect(response).toBeOK();
  }
}

async function seedSingleInquiry(request, sellerId, suffix) {
  const response = await request.post(apiUrl("/api/v1/webhooks/site_form"), {
    headers: { Authorization: `Bearer seller:${sellerId}` },
    data: {
      channel: "site_form",
      channel_message_id: `single-${sellerId}-${suffix}`,
      from: {
        name: "BrightMart Buyer",
        company: "BrightMart Sourcing",
        country: "SG",
        email: `single-${sellerId}-${suffix}@example.com`,
      },
      content: "We need 1800 LED desk lamps with CE certificate and neutral packaging for Singapore.",
      language: "en",
      attachments: [],
      received_at: new Date(Date.UTC(2026, 5, 1, 8, 0)).toISOString(),
    },
  });
  await expect(response).toBeOK();
  return response.json();
}

function panelByTitle(page, title) {
  return page.locator(".panel", { has: page.getByRole("heading", { name: title }) });
}

function apiUrl(path) {
  return API_BASE_URL ? `${API_BASE_URL}${path}` : path;
}

expect.extend({
  async toHaveNoHorizontalOverflow(page) {
    const overflow = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    const pass = overflow.scrollWidth <= overflow.clientWidth;
    return {
      pass,
      message: () => `expected no horizontal overflow, got scrollWidth ${overflow.scrollWidth} and clientWidth ${overflow.clientWidth}`,
    };
  },
  async toHaveVerticalScroll(locator) {
    const overflow = await locator.evaluate((element) => ({
      clientHeight: element.clientHeight,
      scrollHeight: element.scrollHeight,
    }));
    const pass = overflow.scrollHeight > overflow.clientHeight;
    return {
      pass,
      message: () => `expected vertical scroll, got scrollHeight ${overflow.scrollHeight} and clientHeight ${overflow.clientHeight}`,
    };
  },
});
