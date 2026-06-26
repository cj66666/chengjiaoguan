/**
 * [INPUT]: 依赖浏览器内存状态、前端 API 路径与 Wave 3 Demo 固定数据
 * [OUTPUT]: 对外提供 createMockApiClient，用于 GitHub Pages 静态在线 Demo
 * [POS]: frontend/src 的在线演示适配层，让无后端托管环境仍能演示 Agent、Skills、护栏和工作台交互
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */

const nowIso = () => new Date().toISOString();

const wave3Manifest = {
  stage: "semifinal_wave_3",
  goal: "提交可交付最终结果的智能体，整合 Skills 技能，进行产品演示 Demo。",
  agent: {
    name: "Closer Operating Agent",
    runtime: "PydanticAI runtime + Pydantic Graph operating workflow",
    entrypoints: ["run_closer_agent", "run_closer_graph", "POST /api/v1/demo/seed"],
    workflow: ["receive", "qualify", "understand", "quote", "answer", "followup", "handoff", "persist"],
    guardrails: [
      "floor price approval",
      "hard minimum price fuse",
      "sensitive commitment approval",
      "large order approval",
      "low confidence product match handoff",
      "PI generation permission check",
    ],
  },
  skills: [
    ["inquiry-intake", "多渠道询盘接入", "POST /api/v1/webhooks/site_form"],
    ["inquiry-qualification", "询盘甄别评分", "score_inquiry"],
    ["customer-crm", "客户画像与 CRM 建档", "get_customer"],
    ["product-knowledge-match", "产品匹配与知识检索", "match_product + search_knowledge"],
    ["quotation-pi-draft", "报价与 PI 草稿", "calc_quote + generate_pi"],
    ["approval-guardrails", "风险护栏与人工审批", "send_message + request_handoff"],
    ["delivery-followup", "投递记录、重试与跟进", "create_followup + workers/run-due"],
    ["ops-readiness", "原型运维就绪检查", "GET /api/v1/ops/readiness"],
  ].map(([id, name, entrypoint]) => ({ id, name, path: `skills/${id}/SKILL.md`, entrypoint })),
  demo: {
    browser_url: "https://cj66666.github.io/chengjiaoguan/",
    primary_entrypoint: "POST /api/v1/demo/seed",
    script: "python scripts/demo_flow.py --base-url http://127.0.0.1:8000 --approve --run-workers --json",
  },
  verification: {
    backend: "python -m pytest",
    frontend_build: "cd frontend && npm run build",
    frontend_e2e: "cd frontend && npm run test:e2e",
  },
};

const seedProducts = [
  {
    id: 101,
    sku: "DEMO-LAMP-10W",
    name: "LED Desk Lamp 10W",
    status: "active",
    cost: 2.1,
    currency: "USD",
    moq: 500,
    description: "Adjustable LED desk lamp for B2B bulk orders.",
    specs: { power: "10W", certification: "CE", material: "aluminum" },
  },
  {
    id: 102,
    sku: "DEMO-RATTAN-SOFA-5S",
    name: "5-Seater PE Rattan Corner Sofa Set",
    status: "active",
    cost: 128,
    currency: "USD",
    moq: 30,
    description: "Modular outdoor sofa set for garden retailers.",
    specs: { material: "PE rattan", frame: "aluminum" },
  },
  {
    id: 103,
    sku: "DEMO-CANTILEVER-PARASOL-3M",
    name: "3m Cantilever Garden Parasol",
    status: "active",
    cost: 62,
    currency: "USD",
    moq: 60,
    description: "Offset outdoor umbrella for terrace programs.",
    specs: { canopy: "UV50 polyester", pole: "aluminum" },
  },
  {
    id: 104,
    sku: "DEMO-FOLDING-CAMP-CHAIR",
    name: "Folding Outdoor Camping Chair",
    status: "active",
    cost: 9.8,
    currency: "USD",
    moq: 300,
    description: "Portable chair with carry bag.",
    specs: { fabric: "600D oxford", capacity: "120kg" },
  },
];

function initialState(sellerId) {
  const receivedAt = new Date(Date.now() - 8 * 60 * 1000).toISOString();
  const customer = {
    id: 201,
    seller_id: sellerId,
    name: "Jane Buyer",
    company: "ACME Trading",
    country: "US",
    email: "jane.demo@example.com",
    status: "active",
    grade: "A",
  };
  const inquiry = {
    id: 301,
    seller_id: sellerId,
    customer_id: customer.id,
    customer,
    source_channel: "site_form",
    raw_content: "Hi, we need 5000 LED desk lamps shipped to US. Please quote CIF and payment terms.",
    summary: "US · 5000 LED desk lamps · CIF and payment terms requested.",
    status: "pending_approval",
    grade: "A",
    received_at: receivedAt,
  };
  const quotation = {
    id: 401,
    seller_id: sellerId,
    inquiry_id: inquiry.id,
    customer_id: customer.id,
    status: "draft",
    currency: "USD",
    total_amount: 15250,
    valid_until: "2026-06-29",
    hits_floor: true,
    items: [
      { id: 1, product_id: 101, quantity: 5000, unit_price: 3.05, amount: 15250 },
    ],
    terms: {
      message: "AI drafted USD 3.05/unit for 5000 pcs. Outbound send is paused because the customer requested payment terms and floor-price-sensitive conditions.",
    },
  };
  const approval = {
    id: 501,
    seller_id: sellerId,
    conversation_id: 601,
    inquiry_id: inquiry.id,
    type: "message_send",
    reason: "below_floor_price",
    summary: "AI outbound message paused: sensitive_commitment, below_floor_price",
    suggestion: "Keep USD 3.05/unit, offer standard 30% deposit and 70% before shipment, and ask for confirmation.",
    status: "pending",
    payload: {
      quotation_id: quotation.id,
      reasons: ["sensitive_commitment", "below_floor_price"],
    },
    created_at: receivedAt,
  };
  return {
    sellerId,
    seeded: true,
    customers: [
      {
        ...customer,
        inquiries: [inquiry],
        conversations: [{ id: 601, channel: "site_form", status: "ai_active" }],
        quotations: [quotation],
        followups: [{ id: 701, status: "active", next_run_at: "2026-06-16T09:30:00Z" }],
      },
    ],
    inquiries: [inquiry],
    approvals: [approval],
    quotations: [quotation],
    products: [...seedProducts],
    pricingRules: [
      {
        id: 801,
        product_id: 101,
        floor_price: 3,
        margin_rate: 0.3,
        currency: "USD",
        valid_days: 14,
        status: "active",
        logistics_template: { unit_cost: "0.20", hard_min_price: "2.90" },
        tiered_prices: [{ min_qty: 1000, price: "3.30" }, { min_qty: 5000, price: "3.05" }],
      },
    ],
    channels: [
      { id: 901, channel_type: "site_form", name: "Website form", status: "connected", credentials_key_status: "sealed" },
      { id: 902, channel_type: "email", name: "Sales inbox", status: "warning", credentials_key_status: "demo" },
    ],
    notifications: [
      { id: 1001, title: "护栏触发", body: "ACME Trading 报价消息需要人工审批。", severity: "warning", status: "unread" },
    ],
    messages: [
      {
        id: 1101,
        conversation_id: 601,
        sender_role: "customer",
        content: "Hi, we need 5000 LED desk lamps shipped to US. Please quote CIF and payment terms.",
        sent_at: receivedAt,
      },
      {
        id: 1102,
        conversation_id: 601,
        sender_role: "ai",
        content: "Draft prepared, but sending is paused for floor-price and payment-term approval.",
        sent_at: nowIso(),
      },
    ],
    settings: {
      id: sellerId,
      name: "Sunpath Outdoor Mfg.",
      phone: "+86 755 0000 0000",
      plan: "wave3-demo",
      ai_disclosure: true,
      settings: { large_order_approval_threshold: "10000" },
    },
    workers: { due: 0, processed: 0, status: "idle" },
  };
}

const states = new Map();

export function createMockApiClient({ sellerId }) {
  const state = getState(sellerId);
  return {
    get: (path) => mockRequest(state, "GET", path),
    post: (path, body) => mockRequest(state, "POST", path, body),
    put: (path, body) => mockRequest(state, "PUT", path, body),
    patch: (path, body) => mockRequest(state, "PATCH", path, body),
  };
}

function getState(sellerId) {
  if (!states.has(sellerId)) {
    states.set(sellerId, initialState(sellerId));
  }
  return states.get(sellerId);
}

async function mockRequest(state, method, path, body = {}) {
  await new Promise((resolve) => window.setTimeout(resolve, 120));
  const url = new URL(path, "https://demo.local");
  const pathname = url.pathname;

  if (method === "GET" && pathname === "/api/v1/demo/wave3") return clone(wave3Manifest);
  if (method === "POST" && pathname === "/api/v1/demo/seed") return seedDemo(state);
  if (method === "GET" && pathname === "/api/v1/dashboard/metrics") return metrics(state);
  if (method === "GET" && pathname === "/api/v1/inquiries") return collection(state.inquiries);
  if (method === "GET" && pathname === "/api/v1/approvals") return collection(state.approvals);
  if (method === "GET" && pathname === "/api/v1/customers") return collection(state.customers);
  if (method === "GET" && pathname === "/api/v1/products") return collection(state.products);
  if (method === "GET" && pathname === "/api/v1/pricing-rules") return collection(state.pricingRules);
  if (method === "GET" && pathname === "/api/v1/channels") return collection(state.channels);
  if (method === "GET" && pathname === "/api/v1/notifications") return collection(state.notifications.filter((item) => item.status !== "archived"));
  if (method === "GET" && pathname === "/api/v1/ops/readiness") return readiness(state);
  if (method === "GET" && pathname === "/api/v1/settings") return clone(state.settings);
  if (method === "POST" && pathname === "/api/v1/workers/run-due") return runWorkers(state);

  const approvalApprove = pathname.match(/^\/api\/v1\/approvals\/(\d+)\/approve$/);
  if (method === "POST" && approvalApprove) return approveApproval(state, Number(approvalApprove[1]));

  const inquiryPatch = pathname.match(/^\/api\/v1\/inquiries\/(\d+)$/);
  if (method === "PATCH" && inquiryPatch) return patchInquiry(state, Number(inquiryPatch[1]), body);

  const customerGet = pathname.match(/^\/api\/v1\/customers\/(\d+)$/);
  if (method === "GET" && customerGet) return getCustomer(state, Number(customerGet[1]));

  const quotationGet = pathname.match(/^\/api\/v1\/quotations\/(\d+)$/);
  if (method === "GET" && quotationGet) return getQuotation(state, Number(quotationGet[1]));

  const quotationSend = pathname.match(/^\/api\/v1\/quotations\/(\d+)\/send$/);
  if (method === "POST" && quotationSend) return sendQuotation(state, Number(quotationSend[1]));

  const messagesGet = pathname.match(/^\/api\/v1\/conversations\/(\d+)\/messages$/);
  if (method === "GET" && messagesGet) return collection(state.messages.filter((item) => item.conversation_id === Number(messagesGet[1])));

  const takeover = pathname.match(/^\/api\/v1\/conversations\/(\d+)\/takeover$/);
  if (method === "POST" && takeover) return takeoverConversation(state, Number(takeover[1]));

  const sendMessage = pathname.match(/^\/api\/v1\/conversations\/(\d+)\/messages$/);
  if (method === "POST" && sendMessage) return appendHumanMessage(state, Number(sendMessage[1]), body);

  const pricingVersions = pathname.match(/^\/api\/v1\/pricing-rules\/(\d+)\/versions$/);
  if (method === "GET" && pricingVersions) return pricingRuleVersions(state, Number(pricingVersions[1]));

  const pricingUpdate = pathname.match(/^\/api\/v1\/pricing-rules\/(\d+)$/);
  if (method === "PUT" && pricingUpdate) return updatePricingRule(state, Number(pricingUpdate[1]), body);

  const channelRotate = pathname.match(/^\/api\/v1\/channels\/(\d+)\/rotate-credentials$/);
  if (method === "POST" && channelRotate) return rotateChannel(state, Number(channelRotate[1]));

  if (method === "POST" && pathname === "/api/v1/products") return createProduct(state, body);
  if (method === "POST" && pathname === "/api/v1/pricing-rules") return createPricingRule(state, body);
  if (method === "POST" && pathname === "/api/v1/channels") return createChannel(state, body);
  if (method === "PATCH" && pathname === "/api/v1/settings") return saveSettings(state, body);

  const notificationPatch = pathname.match(/^\/api\/v1\/notifications\/(\d+)$/);
  if (method === "PATCH" && notificationPatch) return patchNotification(state, Number(notificationPatch[1]), body);

  return {};
}

function seedDemo(state) {
  state.seeded = true;
  return {
    seller_id: state.sellerId,
    scenario: "site_form_quote_guardrail",
    product_id: state.products[0].id,
    product_ids: state.products.map((item) => item.id),
    customer_id: state.customers[0].id,
    inquiry_id: state.inquiries[0].id,
    conversation_id: 601,
    quotation: state.quotations[0],
    approval: {
      status: state.approvals[0]?.status === "pending" ? "pending_approval" : "approved",
      approval_id: 501,
      reason: "below_floor_price",
      reasons: ["sensitive_commitment", "below_floor_price"],
    },
    followup: { followup_id: 701, status: "active", next_run_at: "2026-06-16T09:30:00Z" },
    score: { grade: "A", score: 92, reasons: ["clear quantity", "target market", "payment terms requested"] },
    product_matches: [{ product_id: 101, confidence: 0.91, name: "LED Desk Lamp 10W" }],
    knowledge: [{ id: 1, source_ref: "demo-lamp-faq", content: "CE certification, neutral packaging, standard payment terms." }],
  };
}

function metrics(state) {
  const pending = state.approvals.filter((item) => item.status === "pending").length;
  return {
    today_inquiries: state.inquiries.length,
    pending_handoffs: pending,
    auto_handle_rate: pending ? 0.67 : 0.86,
    conversion: state.inquiries.filter((item) => item.status === "won").length,
    approval: { pending },
    delivery: { failed: 0, sent: state.approvals.some((item) => item.status === "approved") ? 1 : 0 },
    followup: { due: 0, active: 1 },
    pipeline: { total: state.inquiries.length },
    quotation: { total: state.quotations.length },
  };
}

function readiness(state) {
  return {
    status: "attention",
    checks: [
      { name: "Agent manifest", status: "ready", message: `${wave3Manifest.skills.length} skills exposed for Wave 3 demo.` },
      { name: "Static demo mode", status: "ready", message: "GitHub Pages uses in-browser mock data; local API remains available for full backend runs." },
      { name: "Channel credentials", status: "warning", message: `${state.channels.length} demo channels configured; production credentials are not embedded.` },
    ],
  };
}

function collection(items) {
  return { items: clone(items), total: items.length };
}

function approveApproval(state, approvalId) {
  const approval = state.approvals.find((item) => item.id === approvalId);
  if (approval) approval.status = "approved";
  const inquiry = state.inquiries.find((item) => item.id === approval?.inquiry_id);
  if (inquiry) inquiry.status = "quoted";
  state.messages.push({
    id: nextId(state.messages),
    conversation_id: approval?.conversation_id || 601,
    sender_role: "ai",
    content: "Approved reply sent: USD 3.05/unit, standard 30% deposit and 70% before shipment.",
    sent_at: nowIso(),
  });
  return { status: "approved", approval_id: approvalId };
}

function patchInquiry(state, inquiryId, body) {
  const inquiry = state.inquiries.find((item) => item.id === inquiryId);
  if (inquiry) inquiry.status = body.status || inquiry.status;
  return clone(inquiry || {});
}

function getCustomer(state, customerId) {
  return clone(state.customers.find((item) => item.id === customerId) || state.customers[0]);
}

function getQuotation(state, quotationId) {
  return clone(state.quotations.find((item) => item.id === quotationId) || state.quotations[0]);
}

function sendQuotation(state, quotationId) {
  const quote = state.quotations.find((item) => item.id === quotationId);
  if (quote) quote.status = "sent";
  return clone(quote || {});
}

function takeoverConversation(state, conversationId) {
  for (const customer of state.customers) {
    for (const conversation of customer.conversations || []) {
      if (conversation.id === conversationId) conversation.status = "human_takeover";
    }
  }
  return { status: "human_takeover", conversation_id: conversationId };
}

function appendHumanMessage(state, conversationId, body) {
  const message = {
    id: nextId(state.messages),
    conversation_id: conversationId,
    sender_role: "seller",
    content: body.content || "",
    sent_at: nowIso(),
  };
  state.messages.push(message);
  return clone(message);
}

function runWorkers(state) {
  state.workers = {
    followups: { items: [], total: 0 },
    delivery_retries: { items: [], total: 0 },
    pricing_exchange_rate_refreshes: { items: [], total: 0 },
    email_polls: { items: [{ status: "ok", channel_account_id: 902, fetched: 0, ingested: 0, duplicates: 0 }], total: 1 },
    agent_runs: {
      items: [
        {
          status: "ok",
          inquiry_id: state.inquiries[0]?.id,
          conversation_id: 601,
          inquiry_status: state.inquiries[0]?.status,
          requires_human_review: true,
          approval_id: state.approvals[0]?.id,
          quotation_id: state.quotations[0]?.id,
        },
      ],
      total: 1,
    },
    total_jobs: 2,
    status: "completed",
    ran_at: nowIso(),
  };
  return clone(state.workers);
}

function pricingRuleVersions(state, ruleId) {
  const rule = state.pricingRules.find((item) => item.id === ruleId);
  return collection([
    { id: `${ruleId}-v2`, version: 2, action_type: "update", actor: "demo", snapshot: rule },
    { id: `${ruleId}-v1`, version: 1, action_type: "create", actor: "demo", snapshot: rule },
  ]);
}

function createProduct(state, body) {
  const product = { id: nextId(state.products), status: "active", ...body };
  state.products.unshift(product);
  return clone(product);
}

function createPricingRule(state, body) {
  const rule = { id: nextId(state.pricingRules), status: "active", ...body };
  state.pricingRules.unshift(rule);
  return clone(rule);
}

function updatePricingRule(state, ruleId, body) {
  const rule = state.pricingRules.find((item) => item.id === ruleId);
  if (rule) Object.assign(rule, body);
  return clone(rule || {});
}

function createChannel(state, body) {
  const channel = { id: nextId(state.channels), status: "connected", credentials_key_status: "demo", ...body };
  state.channels.unshift(channel);
  return clone(channel);
}

function rotateChannel(state, channelId) {
  const channel = state.channels.find((item) => item.id === channelId);
  if (channel) channel.credentials_key_status = "rotated";
  return clone(channel || {});
}

function saveSettings(state, body) {
  state.settings = { ...state.settings, ...body, settings: { ...state.settings.settings, ...body.settings } };
  return clone(state.settings);
}

function patchNotification(state, notificationId, body) {
  const notification = state.notifications.find((item) => item.id === notificationId);
  if (notification) notification.status = body.status || notification.status;
  return clone(notification || {});
}

function nextId(items) {
  return Math.max(0, ...items.map((item) => Number(item.id) || 0)) + 1;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}
