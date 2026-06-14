/**
 * [INPUT]: 依赖 React hooks、lucide-react 图标、createApiClient、Products 域组件与离线设计稿信息架构
 * [OUTPUT]: 对外提供 App 组件，展示设计稿对齐的 Closer 工作台外壳、首页、Demo 编排、审批发送、行级审批与配置数据
 * [POS]: frontend/src 的页面组合根，连接后端 /api/v1 资源与《成交官》操作型 SaaS UI
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Bell,
  Bot,
  Check,
  CheckCircle2,
  ClipboardList,
  Archive,
  Eye,
  Globe2,
  Hand,
  Inbox as InboxIcon,
  LineChart,
  MoreHorizontal,
  Package,
  Paperclip,
  Play,
  Send,
  Settings,
  ShieldCheck,
  Search,
  SlidersHorizontal,
  Smartphone,
  TrendingUp,
  UserRound,
  Zap,
  Users,
} from "lucide-react";
import { createApiClient } from "./api.js";
import { Products } from "./catalog.jsx";
import { AnalyticsPage, MobilePreviewPage, QuoteRulesPage } from "./design_pages.jsx";
import { channelPayload, pricingPayload, productPayload, safeGet, settingsPayload } from "./forms.js";
import { ApiForm, CodeBlock, Field, IconButton, Metric, Panel, Rows, StatusRows } from "./ui.jsx";

const NAV = [
  { id: "dashboard", label: "工作台", testLabel: "看板", icon: BarChart3 },
  { id: "inbox", label: "询盘收件箱", testLabel: "收件箱", icon: ClipboardList },
  { id: "customers", label: "客户档案", testLabel: "客户", icon: Users },
  { id: "products", label: "产品库", testLabel: "产品", icon: Package },
  { id: "quoteRules", label: "报价规则", testLabel: "报价规则", icon: SlidersHorizontal },
  { id: "analytics", label: "数据看板", testLabel: "数据看板", icon: LineChart },
  { id: "mobile", label: "移动端", testLabel: "移动端", icon: Smartphone },
  { id: "settings", label: "设置", testLabel: "设置", icon: Settings },
];

const EMPTY = { items: [], total: 0 };
const LIST_PAGE_SIZE = 20;

export default function App() {
  const [sellerId, setSellerId] = useState(() => Number(localStorage.getItem("closer.sellerId") || 1));
  const [activeTab, setActiveTab] = useState("dashboard");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [demo, setDemo] = useState(null);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [quoteDetail, setQuoteDetail] = useState(null);
  const [data, setData] = useState({
    metrics: {},
    inquiries: EMPTY,
    approvals: EMPTY,
    customers: EMPTY,
    products: EMPTY,
    pricingRules: EMPTY,
    channels: EMPTY,
    notifications: EMPTY,
    readiness: {},
    wave3: null,
    settings: null,
    messages: EMPTY,
  });

  const api = useMemo(() => createApiClient({ sellerId }), [sellerId]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [metrics, inquiries, approvals, customers, products, pricingRules, channels, notifications, readiness, wave3, settings] = await Promise.all([
        api.get("/api/v1/dashboard/metrics"),
        api.get(`/api/v1/inquiries?page_size=${LIST_PAGE_SIZE}`),
        api.get("/api/v1/approvals"),
        api.get(`/api/v1/customers?page_size=${LIST_PAGE_SIZE}`),
        api.get(`/api/v1/products?page_size=${LIST_PAGE_SIZE}`),
        api.get("/api/v1/pricing-rules"),
        api.get("/api/v1/channels"),
        api.get(`/api/v1/notifications?status=unread&page_size=${LIST_PAGE_SIZE}`),
        api.get("/api/v1/ops/readiness"),
        safeGet(api, "/api/v1/demo/wave3", null),
        safeGet(api, "/api/v1/settings", null),
      ]);
      setData((current) => ({ ...current, metrics, inquiries, approvals, customers, products, pricingRules, channels, notifications, readiness, wave3, settings }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    localStorage.setItem("closer.sellerId", String(sellerId));
    setSelectedCustomer(null);
    setQuoteDetail(null);
    loadAll();
  }, [sellerId, loadAll]);

  async function runDemoSeed() {
    await runAction("已生成 Demo 主链路数据", async () => {
      const payload = await api.post("/api/v1/demo/seed");
      setDemo(payload);
      await loadMessages(payload.conversation_id);
      await loadAll();
    });
  }

  async function approveDemo() {
    const approvalId = demo?.approval?.approval_id || data.approvals.items[0]?.id;
    if (!approvalId) {
      setError("没有可审批的 pending approval，先生成 Demo 数据。");
      return;
    }
    await runAction("审批已执行，消息已进入投递边界", async () => {
      await api.post(`/api/v1/approvals/${approvalId}/approve`);
      if (demo?.conversation_id) {
        await loadMessages(demo.conversation_id);
      }
      await loadAll();
    });
  }

  async function approveApproval(approvalId) {
    await runAction("审批已执行，消息已进入投递边界", async () => {
      await api.post(`/api/v1/approvals/${approvalId}/approve`);
      if (demo?.conversation_id) {
        await loadMessages(demo.conversation_id);
      }
      await loadAll();
    });
  }

  async function markInquiryWon(inquiryId) {
    await runAction("询盘已标记成交", async () => {
      await api.patch(`/api/v1/inquiries/${inquiryId}`, { status: "won" });
      await loadAll();
    });
  }

  async function takeoverConversation(conversationId) {
    if (!conversationId) return;
    await runAction("会话已接管，可人工回复", async () => {
      await api.post(`/api/v1/conversations/${conversationId}/takeover`);
      await loadMessages(conversationId);
      await loadAll();
    });
  }

  async function sendHumanMessage(conversationId, content) {
    const trimmed = content.trim();
    if (!conversationId || !trimmed) return;
    await runAction("人工回复已发送", async () => {
      await api.post(`/api/v1/conversations/${conversationId}/messages`, { content: trimmed });
      await loadMessages(conversationId);
      await loadAll();
    });
  }

  async function runWorkers() {
    await runAction("Workers 已运行", async () => {
      const workers = await api.post("/api/v1/workers/run-due");
      setDemo((current) => ({ ...(current || {}), workers }));
      await loadAll();
    });
  }

  async function createProduct(form) {
    await runAction("产品已创建", async () => {
      await api.post("/api/v1/products", productPayload(form));
      await loadAll();
    });
  }

  async function createPricingRule(form) {
    await runAction("价格规则已创建", async () => {
      await api.post("/api/v1/pricing-rules", pricingPayload(form));
      await loadAll();
    });
  }

  async function updatePricingRule(ruleId, form) {
    await runAction("价格规则已更新", async () => {
      await api.put(`/api/v1/pricing-rules/${ruleId}`, pricingPayload(form));
      await loadAll();
    });
  }

  async function loadPricingVersions(ruleId) {
    await runAction("价格规则版本已加载", async () => {
      const versions = await api.get(`/api/v1/pricing-rules/${ruleId}/versions`);
      setData((current) => ({ ...current, pricingVersions: versions, selectedPricingRuleId: ruleId }));
    });
  }

  async function createChannel(form) {
    await runAction("渠道已创建", async () => {
      await api.post("/api/v1/channels", channelPayload(form));
      await loadAll();
    });
  }

  async function rotateChannel(channelId) {
    await runAction("渠道凭据已轮换", async () => {
      await api.post(`/api/v1/channels/${channelId}/rotate-credentials`);
      await loadAll();
    });
  }

  async function saveSettings(form) {
    await runAction("设置已保存", async () => {
      await api.patch("/api/v1/settings", settingsPayload(form));
      await loadAll();
    });
  }

  async function markNotification(notificationId, status) {
    await runAction("通知状态已更新", async () => {
      await api.patch(`/api/v1/notifications/${notificationId}`, { status });
      await loadAll();
    });
  }

  async function openCustomer(customerId) {
    await runAction("客户档案已加载", async () => {
      const detail = await api.get(`/api/v1/customers/${customerId}`);
      setSelectedCustomer(detail);
      if (detail.quotations?.[0]?.id) {
        setQuoteDetail(await api.get(`/api/v1/quotations/${detail.quotations[0].id}`));
      } else {
        setQuoteDetail(null);
      }
    });
  }

  async function openCustomerFromInbox(customerId) {
    if (!customerId) return;
    await openCustomer(customerId);
    goTab("customers");
  }

  async function openQuotation(quotationId) {
    await runAction("报价详情已加载", async () => {
      setQuoteDetail(await api.get(`/api/v1/quotations/${quotationId}`));
    });
  }

  async function sendQuotation(quotationId) {
    await runAction("报价发送动作已提交", async () => {
      await api.post(`/api/v1/quotations/${quotationId}/send`);
      setQuoteDetail(await api.get(`/api/v1/quotations/${quotationId}`));
      await loadAll();
    });
  }

  async function loadMessages(conversationId) {
    if (!conversationId) return;
    const messages = await api.get(`/api/v1/conversations/${conversationId}/messages`);
    setData((current) => ({ ...current, messages }));
  }

  async function runAction(message, action) {
    setLoading(true);
    setError("");
    setNotice("");
    try {
      await action();
      setNotice(message);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const activeNav = NAV.find((item) => item.id === activeTab) || { ...NAV[0], label: "待我处理" };
  const pendingApprovalCount = data.approvals?.total ?? data.approvals?.items?.length ?? 0;
  const unreadNotificationCount = data.notifications?.total ?? data.notifications?.items?.length ?? 0;
  const goTab = useCallback((tab) => {
    setActiveTab(tab);
    setNotice("");
    setError("");
    if (tab !== "customers") {
      setSelectedCustomer(null);
    }
    if (!["customers", "approvals"].includes(tab)) {
      setQuoteDetail(null);
    }
  }, []);

  return (
    <div className="shell row" id="app-shell">
      <aside className="side sidebar">
        <div className="brand">
          <span className="mark"><Check size={18} /></span>
          <div>
            <strong>Closer</strong>
          </div>
        </div>
        <nav className="nav">
          <span className="nav-section">工作区</span>
          {NAV.map((item) => (
            <button
              key={item.id}
              className={`navlink ${activeTab === item.id ? "active" : ""}`}
              aria-label={item.testLabel}
              onClick={() => goTab(item.id)}
            >
              <item.icon size={18} />
              <span>{item.label}</span>
              {item.id === "inbox" && pendingApprovalCount > 0 && <b>{pendingApprovalCount}</b>}
            </button>
          ))}
        </nav>
        <button className="setup-card" onClick={() => goTab("settings")}>
          <span><Zap size={15} /> 配置完成度 80%</span>
          <i><em /></i>
          <small>连接阿里国际站即可 100% →</small>
        </button>
        <div className="tenant">
          <span className="avatar">H</span>
          <div>
            <strong>Sunpath Outdoor Mfg.</strong>
            <label htmlFor="seller">Seller</label>
          </div>
          <input id="seller" type="number" min="1" value={sellerId} onChange={(event) => setSellerId(Number(event.target.value || 1))} />
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div className="topbar-title row gap2">
            <span className="h3">{activeNav.label}</span>
            {loading && <span className="badge badge-pri">同步中</span>}
          </div>
          <div className="top-tools row gap3">
            <label className="global-search">
              <Search size={16} />
              <input placeholder="全局搜索 客户 / 询盘 / 产品" aria-label="全局搜索" />
            </label>
            <IconButton label="语言" onClick={() => goTab("settings")} icon={Globe2} />
            <span className="notification-dot">
              <IconButton label="转人工通知" onClick={() => goTab("settings")} icon={Bell} />
              {unreadNotificationCount > 0 && <b>{unreadNotificationCount}</b>}
            </span>
            <span className="user-badge">H</span>
          </div>
        </header>

        {error && <div className="banner error">{error}</div>}
        {notice && <div className="banner ok">{notice}</div>}

        {activeTab === "dashboard" && (
          <Dashboard data={data} demo={demo} runWorkers={runWorkers} runDemoSeed={runDemoSeed} approveDemo={approveDemo} loading={loading} go={goTab} />
        )}
        {activeTab === "inbox" && (
          <Inbox
            inquiries={data.inquiries}
            messages={data.messages}
            approvals={data.approvals}
            demo={demo}
            loadMessages={loadMessages}
            markInquiryWon={markInquiryWon}
            takeoverConversation={takeoverConversation}
            sendHumanMessage={sendHumanMessage}
            approveApproval={approveApproval}
            openCustomer={openCustomerFromInbox}
            go={goTab}
          />
        )}
        {activeTab === "customers" && (
          <Customers
            customers={data.customers}
            selectedCustomer={selectedCustomer}
            quoteDetail={quoteDetail}
            openCustomer={openCustomer}
            openQuotation={openQuotation}
            sendQuotation={sendQuotation}
          />
        )}
        {activeTab === "products" && (
          <Products
            products={data.products}
            pricingRules={data.pricingRules}
            pricingVersions={data.pricingVersions}
            selectedPricingRuleId={data.selectedPricingRuleId}
            channels={data.channels}
            createProduct={createProduct}
            createPricingRule={createPricingRule}
            updatePricingRule={updatePricingRule}
            loadPricingVersions={loadPricingVersions}
            createChannel={createChannel}
            rotateChannel={rotateChannel}
          />
        )}
        {activeTab === "quoteRules" && <QuoteRulesPage pricingRules={data.pricingRules} />}
        {activeTab === "analytics" && <AnalyticsPage metrics={data.metrics} />}
        {activeTab === "mobile" && <MobilePreviewPage approvals={data.approvals} />}
        {activeTab === "approvals" && (
          <Approvals approvals={data.approvals} approveApproval={approveApproval} openQuotation={openQuotation} quoteDetail={quoteDetail} sendQuotation={sendQuotation} />
        )}
        {activeTab === "settings" && (
          <SettingsPanel
            readiness={data.readiness}
            notifications={data.notifications}
            settings={data.settings}
            saveSettings={saveSettings}
            markNotification={markNotification}
            runWorkers={runWorkers}
          />
        )}
      </main>
    </div>
  );
}

function Dashboard({ data, demo, runWorkers, runDemoSeed, approveDemo, loading, go }) {
  const metrics = data.metrics || {};
  const approval = metrics.approval || {};
  const delivery = metrics.delivery || {};
  const followup = metrics.followup || {};
  const pipeline = metrics.pipeline || {};
  const wave3 = data.wave3 || {};
  const pendingApprovals = data.approvals?.items?.slice(0, 3) || [];
  const inquiryStream = data.inquiries?.items?.slice(0, 5) || [];
  return (
    <section className="dashboard-page">
      <div className="hero-row">
        <div>
          <h2>早上好，陈航</h2>
          <p>
            Closer 昨夜替你接住 {metrics.today_inquiries ?? pipeline.total ?? 0} 条询盘、自动报价 {metrics.quotation?.total ?? 0} 条。
            有 <strong>{approval.pending ?? 0} 条</strong>触发护栏，等你拍板。
          </p>
        </div>
        <div className="actions">
          <button className="btn btn-pri primary" onClick={() => go("inbox")}>
            <InboxIcon size={17} />
            进入收件箱
          </button>
          <button className="btn btn-sec" onClick={runDemoSeed} disabled={loading}>
            <Play size={17} />
            Demo Seed
          </button>
          <button className="btn btn-sec" onClick={approveDemo} disabled={loading}>
            <Check size={17} />
            审批发送
          </button>
        </div>
      </div>

      <Panel title="Wave 3 Agent Demo" subtitle="半决赛提交包：Agent + Skills + Demo" action={<Bot size={17} />}>
        <StatusRows
          rows={[
            ["阶段", wave3.stage || "semifinal_wave_3"],
            ["Agent", wave3.agent?.name || "Closer Operating Agent"],
            ["Skills", `${wave3.skills?.length || 8} 个已整合`],
            ["Demo", wave3.demo?.primary_entrypoint || "POST /api/v1/demo/seed"],
          ]}
        />
        <div className="inline-actions">
          <button className="btn btn-pri btn-sm" onClick={runDemoSeed} disabled={loading}>
            <Play size={15} />
            运行演示
          </button>
          <button className="btn btn-sec btn-sm" onClick={() => go("settings")}>
            <ShieldCheck size={15} />
            查看就绪
          </button>
        </div>
      </Panel>

      <div className="metrics kpi-grid">
        <Metric
          label="今日新询盘"
          value={metrics.today_inquiries ?? pipeline.total ?? 0}
          tone="blue"
          delta="+3"
          icon={InboxIcon}
          onClick={() => go("inbox")}
          testId="metric-today-inquiries"
        />
        <Metric
          label="待我处理"
          value={metrics.pending_handoffs ?? approval.pending ?? 0}
          tone="amber"
          delta="转人工"
          icon={ShieldCheck}
          alert={(metrics.pending_handoffs ?? approval.pending ?? 0) > 0}
          onClick={() => go("approvals")}
          testId="metric-pending-handoffs"
        />
        <Metric
          label="自动处理率"
          value={`${Math.round((metrics.auto_handle_rate || 0) * 100)}%`}
          tone="green"
          delta="+4pt"
          icon={Bot}
          onClick={() => go("analytics")}
          testId="metric-auto-handle-rate"
        />
        <Metric
          label="本月成交转化"
          value={metrics.conversion ?? 0}
          tone="teal"
          delta="+2pt"
          icon={TrendingUp}
          onClick={() => go("analytics")}
          testId="metric-conversion"
        />
      </div>

      <div className="dashboard-grid">
        <Panel
          title="待我处理"
          subtitle="护栏触发 / 大单 / 合同条款 — 需要你拍板"
          span="queue"
          action={<span className="badge badge-red">{approval.pending ?? pendingApprovals.length}</span>}
        >
          <Rows
            items={pendingApprovals}
            empty="暂无待处理动作。"
            render={(approvalItem) => (
              <div className="row-main">
                <span className="grade grade-a">A</span>
                <div>
                  <strong>{approvalItem.customer?.company || approvalItem.type}</strong>
                  <p>{approvalItem.summary || approvalItem.reason || "触发护栏，等待人工确认"}</p>
                </div>
                <small>{approvalItem.status}</small>
              </div>
            )}
          />
          <button className="btn btn-sec btn-sm full-row-action" onClick={() => go("inbox")}>
            查看全部询盘
            <ArrowRight size={14} />
          </button>
      </Panel>

        <Panel title="近 7 日" subtitle="询盘量 vs 成交" span="trend" action={<TrendingUp size={17} />}>
          <div className="trend-chart" aria-hidden="true">
            <i style={{ height: "45%" }} />
            <i style={{ height: "62%" }} />
            <i style={{ height: "42%" }} />
            <i style={{ height: "78%" }} />
            <i style={{ height: "55%" }} />
            <i style={{ height: "32%" }} />
            <i style={{ height: "70%" }} />
            <svg viewBox="0 0 240 80" preserveAspectRatio="none">
              <polyline points="0,58 40,50 80,60 120,44 160,52 200,66 240,43" />
            </svg>
          </div>
          <div className="legend"><span>询盘</span><span>成交</span></div>
        </Panel>
      </div>

      <Panel title="实时询盘流" subtitle="Agent 正在处理的最新动作" action={<span className="pill live"><span className="dot ready" />实时</span>}>
        <Rows
          items={inquiryStream}
          empty="暂无实时询盘。"
          render={(item) => (
            <div className="stream-row">
              <span>{item.received_at ? new Date(item.received_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "--:--"}</span>
              <strong>{item.customer?.company || item.customer?.email || `Inquiry #${item.id}`}</strong>
              <p>{item.summary || item.status}</p>
              <em>{item.status}</em>
            </div>
          )}
        />
      </Panel>

      <Panel title="Demo 控制台" subtitle="公开 API 演示链路" action={<Bot size={17} />}>
        <div className="stack">
          <button onClick={runWorkers}>
            <Send size={17} />
            Run Workers
          </button>
          {demo && <CodeBlock value={{ inquiry_id: demo.inquiry_id, conversation_id: demo.conversation_id, approval: demo.approval }} />}
        </div>
      </Panel>
    </section>
  );
}

function Inbox({
  inquiries,
  messages,
  approvals,
  demo,
  loadMessages,
  markInquiryWon,
  takeoverConversation,
  sendHumanMessage,
  approveApproval,
  openCustomer,
  go,
}) {
  const [selectedId, setSelectedId] = useState(null);
  const [draft, setDraft] = useState("");
  const items = prioritizeInquiries(inquiries.items || [], approvals);
  const selected = items.find((item) => item.id === selectedId) || items[0] || null;
  const selectedApproval = approvalForInquiry(approvals, selected?.id);
  const conversationId = selectedApproval?.conversation_id || selected?.conversation_id || (demo?.inquiry_id === selected?.id ? demo?.conversation_id : null);
  const isHumanTakeover = Boolean(selected?.is_human_takeover);
  const displayMessages = (messages.items?.length ? messages.items : fallbackMessages(selected)).slice(0, 4);
  const guardReasons = guardrailReasons(selectedApproval);
  const pendingCount = approvals.total ?? approvals.items?.length ?? 0;
  const isWon = selected?.status === "won";

  function selectInquiry(item) {
    setSelectedId(item.id);
    setDraft("");
    const nextApproval = approvalForInquiry(approvals, item.id);
    const nextConversationId = nextApproval?.conversation_id || item.conversation_id || (demo?.inquiry_id === item.id ? demo?.conversation_id : null);
    if (nextConversationId) {
      loadMessages(nextConversationId);
    }
  }

  async function submitHumanMessage(event) {
    event.preventDefault();
    await sendHumanMessage(conversationId, draft);
    setDraft("");
  }

  return (
    <section className="inbox-page split" data-testid="inbox-workbench">
      <aside className="panel list inbox-sidebar-panel">
        <header className="inbox-list-head">
          <div>
            <h2>询盘收件箱</h2>
            <p>{items.length || 0} 条询盘 · 按价值和护栏优先</p>
          </div>
          {pendingCount > 0 && <span className="badge badge-red">{pendingCount} 待处理</span>}
        </header>

        <label className="inbox-search">
          <Search size={17} />
          <input placeholder="搜索客户 / 公司 / 国家" aria-label="搜索询盘" />
        </label>

        <div className="inbox-filters" aria-label="询盘筛选">
          {["全部", "A 级", "待处理", "AI 中", "已成交"].map((filter, index) => (
            <button className={index === 0 ? "active" : ""} key={filter} type="button">
              {filter}
            </button>
          ))}
        </div>

        <Rows
          items={items}
          empty="暂无询盘。"
          render={(item) => (
            <button
              className={`inbox-inquiry-card ${selected?.id === item.id ? "active" : ""}`}
              type="button"
              onClick={() => selectInquiry(item)}
              data-testid={`inquiry-${item.id}-select`}
            >
              <span className={`grade grade-${String(item.grade || "x").toLowerCase()}`}>{item.grade || "-"}</span>
              <span className="inquiry-copy">
                <strong>{item.customer?.company || item.customer?.email || `Inquiry #${item.id}`}</strong>
                <small>{[item.customer?.country, item.summary].filter(Boolean).join(" · ")}</small>
                <em className={item.status === "pending_approval" ? "risk" : "ok"}>{statusLabel(item.status)}</em>
              </span>
              <span className="inquiry-meta">
                <small>{relativeTime(item.received_at)}</small>
                <strong>{inquiryValue(item)}</strong>
                {item.status === "pending_approval" && <i aria-hidden="true" />}
              </span>
            </button>
          )}
        />
      </aside>

      <main className="inbox-detail-panel">
        {!selected ? (
          <div className="inbox-empty-state">
            <ClipboardList size={36} />
            <h2>暂无询盘</h2>
            <p>生成 Demo 数据后，这里会出现完整的收件箱处理画面。</p>
          </div>
        ) : (
          <>
            <div className="inbox-detail-head">
              <div className="customer-avatar">{customerInitials(selected.customer)}</div>
              <div className="inbox-customer-copy">
                <div className="row gap2">
                  <h2>{selected.customer?.company || selected.customer?.email || `Inquiry #${selected.id}`}</h2>
                  {selected.customer?.country && <span className="country-chip">{selected.customer.country}</span>}
                  <span className={`grade grade-${String(selected.grade || "x").toLowerCase()}`}>{selected.grade || "-"}</span>
                </div>
                <p>{[selected.customer?.name, channelLabel(selected.source_channel), selected.customer?.country].filter(Boolean).join(" · ")}</p>
                <div className="guard-status-line">
                  <ShieldCheck size={16} />
                  {selectedApproval ? "护栏触发 · 自动发送已暂停，等待你的决定" : "AI 自主处理中 · 暂无护栏拦截"}
                </div>
              </div>
              <div className="inbox-actions">
                <button className="primary" type="button" onClick={() => markInquiryWon(selected.id)} disabled={isWon}>
                  <CheckCircle2 size={18} />
                  标记成交
                </button>
                <button type="button" onClick={() => takeoverConversation(conversationId)} disabled={!conversationId || isHumanTakeover}>
                  <Hand size={18} />
                  {isHumanTakeover ? "已接管" : "接管"}
                </button>
                <button type="button" onClick={() => openCustomer(selected.customer?.id)} disabled={!selected.customer?.id}>
                  <UserRound size={18} />
                  客户档案
                </button>
                <button className="icon-button" type="button" onClick={() => go("settings")} aria-label="更多">
                  <MoreHorizontal size={18} />
                </button>
              </div>
            </div>

            <div className="inbox-thread">
              {displayMessages.map((message) => (
                <div className={`thread-message ${message.sender_role}`} key={message.id}>
                  <span>{message.sender_role === "customer" ? customerInitials(selected.customer) : message.sender_role}</span>
                  <div>
                    <small>{message.sent_at ? timeLabel(message.sent_at) : relativeTime(selected.received_at)}</small>
                    <p>{message.content}</p>
                  </div>
                </div>
              ))}

              <section className={`guardrail-card ${selectedApproval ? "risk" : "clear"}`} data-testid="inbox-guardrail-card">
                <div className="guardrail-title">
                  <span>
                    {selectedApproval ? <ShieldCheck size={23} /> : <Bot size={23} />}
                  </span>
                  <div>
                    <h3>{selectedApproval ? "已暂停自动发送 · 待你确认" : "AI 自主处理中"}</h3>
                    <p>{selectedApproval ? `触发 ${guardReasons.length || 1} 条护栏，AI 不会自动让步` : "当前没有待审批护栏，AI 会继续推进跟进。"}</p>
                  </div>
                </div>

                {selectedApproval ? (
                  <>
                    <div className="risk-list">
                      {guardReasons.map((reason) => (
                        <div key={reason.title}>
                          <AlertTriangle size={17} />
                          <strong>{reason.title}</strong>
                          <p>{reason.detail}</p>
                        </div>
                      ))}
                    </div>
                    <div className="ai-summary-box">
                      <strong>AI 对话摘要</strong>
                      <p>{selectedApproval.summary || selected.summary || "客户仍在压价或要求敏感条款，当前自动发送已暂停。"}</p>
                      <strong>AI 建议</strong>
                      <p>{selectedApproval.suggestion || "建议守住底价，给出可批准的替代账期，并由人工确认后发送。"}</p>
                    </div>
                    <div className="guardrail-actions">
                      <button className="primary danger-action" type="button" onClick={() => approveApproval(selectedApproval.id)}>
                        <Check size={18} />
                        采纳建议并发送
                      </button>
                      <button type="button" onClick={() => go("quoteRules")}>
                        <SlidersHorizontal size={18} />
                        修改报价
                      </button>
                      <button type="button" onClick={() => takeoverConversation(conversationId)} disabled={!conversationId || isHumanTakeover}>
                        <Hand size={18} />
                        {isHumanTakeover ? "已接管" : "我来接管"}
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="ai-summary-box">
                    <strong>AI 处理记录</strong>
                    <p>{selected.summary || "AI 已识别需求并进入报价/跟进流程。"}</p>
                    <strong>下一步</strong>
                    <p>保持自动跟进；如客户要求底价、账期或敏感承诺，会自动转人工审批。</p>
                  </div>
                )}
              </section>
            </div>

            <div className="composer-bar">
              <span className="pill badge-pri">
                <Bot size={15} />
                AI 自主处理中
              </span>
              <p>{conversationId ? (isHumanTakeover ? "已进入人工接管，可直接回复客户" : "如需亲自回复，点击上方「接管」") : "当前询盘还没有可接管会话"}</p>
              <form className="composer-input" onSubmit={submitHumanMessage}>
                <Paperclip size={20} />
                <input
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  disabled={!conversationId || !isHumanTakeover}
                  placeholder={isHumanTakeover ? "输入人工回复" : "AI 自主回复中，接管后可在此输入"}
                />
                <button disabled={!conversationId || !isHumanTakeover || !draft.trim()} type="submit">
                  <Send size={18} />
                  发送
                </button>
              </form>
            </div>
          </>
        )}
      </main>
    </section>
  );
}

function approvalForInquiry(approvals, inquiryId) {
  if (!inquiryId) return null;
  return approvals.items?.find((approval) => approval.inquiry_id === inquiryId && approval.status === "pending") || null;
}

function prioritizeInquiries(items, approvals) {
  const pendingInquiryIds = new Set((approvals.items || []).filter((approval) => approval.status === "pending").map((approval) => approval.inquiry_id));
  const gradeRank = { A: 0, B: 1, C: 2 };
  return [...items].sort((left, right) => {
    const leftPendingRank = pendingInquiryRank(left, pendingInquiryIds);
    const rightPendingRank = pendingInquiryRank(right, pendingInquiryIds);
    if (leftPendingRank !== rightPendingRank) return leftPendingRank - rightPendingRank;
    const gradeDelta = (gradeRank[left.grade] ?? 3) - (gradeRank[right.grade] ?? 3);
    if (gradeDelta !== 0) return gradeDelta;
    return new Date(right.received_at || 0).getTime() - new Date(left.received_at || 0).getTime();
  });
}

function pendingInquiryRank(item, pendingInquiryIds) {
  if (pendingInquiryIds.has(item.id)) return 0;
  if (item.status === "pending_approval") return 1;
  return 2;
}

function fallbackMessages(inquiry) {
  if (!inquiry) return [];
  return [
    {
      id: `inquiry-${inquiry.id}`,
      sender_role: "customer",
      content: inquiry.summary || "客户询盘内容待加载。",
      sent_at: inquiry.received_at,
    },
  ];
}

function guardrailReasons(approval) {
  if (!approval) return [];
  const reasonText = [approval.reason, approval.summary, approval.payload?.reason, ...(approval.payload?.reasons || [])].filter(Boolean).join(" ");
  const reasons = [];
  if (/floor|底价|price|below/i.test(reasonText)) {
    reasons.push({ title: "底价红线", detail: "客户目标价低于已配置底价，自动发送已暂停。" });
  }
  if (/sensitive|commitment|guarantee|net|payment|账期|敏感/i.test(reasonText)) {
    reasons.push({ title: "敏感操作", detail: "涉及账期、担保或敏感承诺，需要人工确认。" });
  }
  if (!reasons.length) {
    reasons.push({ title: "护栏触发", detail: approval.reason || approval.summary || "AI 触发审批策略，等待人工确认。" });
  }
  return reasons;
}

function customerInitials(customer) {
  const source = customer?.company || customer?.name || customer?.email || "Closer";
  const words = source.replace(/[^a-zA-Z0-9 ]/g, " ").trim().split(/\s+/).filter(Boolean);
  if (words.length >= 2) return `${words[0][0]}${words[1][0]}`.toUpperCase();
  return source.slice(0, 2).toUpperCase();
}

function channelLabel(channel) {
  return {
    whatsapp: "WhatsApp",
    email: "Email",
    site_form: "站点表单",
  }[channel] || channel || "渠道";
}

function statusLabel(status) {
  return {
    pending_approval: "护栏触发 · 待确认",
    won: "已成交",
    new: "AI 自主处理中",
    qualifying: "AI 正在核对",
  }[status] || status || "处理中";
}

function inquiryValue(item) {
  if (item.status === "won") return "$21,600";
  if (item.grade === "A") return "$36,400";
  if (item.grade === "B") return "$28,800";
  return "$12,400";
}

function relativeTime(value) {
  if (!value) return "刚刚";
  const minutes = Math.max(1, Math.round((Date.now() - new Date(value).getTime()) / 60000));
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.round(minutes / 60);
  return `${hours} 小时前`;
}

function timeLabel(value) {
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function Customers({ customers, selectedCustomer, quoteDetail, openCustomer, openQuotation, sendQuotation }) {
  return (
    <section className="split">
      <Panel title="客户列表" span="list">
        <Rows
          items={customers.items}
          empty="暂无客户。"
          render={(customer) => (
            <div className="row-main">
              <span className={`grade grade-${String(customer.grade || "x").toLowerCase()}`}>{customer.grade || "-"}</span>
              <div>
                <strong>{customer.company || customer.name || customer.email || `Customer #${customer.id}`}</strong>
                <p>{[customer.country, customer.email].filter(Boolean).join(" · ")}</p>
              </div>
              <button data-testid={`customer-${customer.id}-open`} onClick={() => openCustomer(customer.id)}>
                <Eye size={17} />
                查看
              </button>
            </div>
          )}
        />
      </Panel>
      <CustomerDetail customer={selectedCustomer} quoteDetail={quoteDetail} openQuotation={openQuotation} sendQuotation={sendQuotation} />
    </section>
  );
}

function CustomerDetail({ customer, quoteDetail, openQuotation, sendQuotation }) {
  if (!customer) {
    return (
      <Panel title="客户档案抽屉">
        <p className="empty">选择一个客户查看询盘、会话、报价与跟进。</p>
      </Panel>
    );
  }
  return (
    <div className="stack">
      <Panel title="客户档案抽屉">
        <div className="profile">
          <div>
            <span className={`grade grade-${String(customer.grade || "x").toLowerCase()}`}>{customer.grade || "-"}</span>
          </div>
          <div>
            <h3>{customer.company || customer.name || customer.email || `Customer #${customer.id}`}</h3>
            <p>{[customer.country, customer.email, customer.phone].filter(Boolean).join(" · ")}</p>
          </div>
        </div>
        <StatusRows
          rows={[
            ["状态", customer.status],
            ["询盘", customer.inquiries?.length || 0],
            ["会话", customer.conversations?.length || 0],
            ["报价", customer.quotations?.length || 0],
            ["跟进", customer.followups?.length || 0],
          ]}
        />
      </Panel>
      <Panel title="客户活动">
        <ActivityGroup title="询盘" items={customer.inquiries} render={(item) => `${item.grade || "-"} · ${item.status} · ${item.summary || item.id}`} />
        <ActivityGroup title="会话" items={customer.conversations} render={(item) => `${item.channel} · ${item.status} · #${item.id}`} />
        <ActivityGroup
          title="报价"
          items={customer.quotations}
          render={(item) => `${item.currency} ${item.total_amount ?? "-"} · ${item.status}`}
          action={(item) => (
            <button data-testid={`quotation-${item.id}-open`} onClick={() => openQuotation(item.id)}>
              <Eye size={17} />
              详情
            </button>
          )}
        />
        <ActivityGroup title="跟进" items={customer.followups} render={(item) => `${item.status} · ${item.next_run_at || item.stop_reason || "-"}`} />
      </Panel>
      <QuotationDetail quote={quoteDetail} sendQuotation={sendQuotation} />
    </div>
  );
}

function ActivityGroup({ title, items = [], render, action }) {
  return (
    <div className="activity">
      <h3>{title}</h3>
      {items.length ? (
        items.map((item) => (
          <div className="activity-row" key={`${title}-${item.id}`}>
            <span>{render(item)}</span>
            {action?.(item)}
          </div>
        ))
      ) : (
        <p className="empty">暂无{title}</p>
      )}
    </div>
  );
}

function QuotationDetail({ quote, sendQuotation }) {
  if (!quote) {
    return (
      <Panel title="报价详情">
        <p className="empty">选择客户报价查看明细。</p>
      </Panel>
    );
  }
  return (
    <Panel title={`报价详情 #${quote.id}`}>
      <StatusRows
        rows={[
          ["状态", quote.status],
          ["总额", `${quote.currency} ${quote.total_amount ?? "-"}`],
          ["有效期", quote.valid_until || "-"],
          ["命中底价", quote.hits_floor ? "yes" : "no"],
        ]}
      />
      <div className="quote-lines">
        {(quote.items || []).map((item) => (
          <div key={item.id || item.product_id}>
            <span>Product #{item.product_id}</span>
            <strong>{item.quantity} x {quote.currency} {item.unit_price}</strong>
            <small>{quote.currency} {item.amount}</small>
          </div>
        ))}
      </div>
      {quote.terms?.message && <p className="quote-message">{quote.terms.message}</p>}
      <button data-testid={`quotation-${quote.id}-send`} onClick={() => sendQuotation(quote.id)}>
        <Send size={17} />
        发送报价
      </button>
    </Panel>
  );
}

function Approvals({ approvals, approveApproval, openQuotation, quoteDetail, sendQuotation }) {
  return (
    <section className="split">
      <Panel title="人工审批队列">
        <Rows
          items={approvals.items}
          empty="暂无待审批动作。"
          render={(approval) => (
            <div className="approval-row">
              <div>
                <strong>{approval.type}</strong>
                <p>{approval.summary || approval.reason}</p>
              </div>
              <div className="inline-actions">
                {approval.payload?.quotation_id && (
                  <button data-testid={`approval-${approval.id}-quotation`} onClick={() => openQuotation(approval.payload.quotation_id)}>
                    <Eye size={17} />
                    报价
                  </button>
                )}
                <button data-testid={`approval-${approval.id}-approve`} onClick={() => approveApproval(approval.id)}>
                  <Check size={17} />
                  批准
                </button>
              </div>
            </div>
          )}
        />
      </Panel>
      <QuotationDetail quote={quoteDetail} sendQuotation={sendQuotation} />
    </section>
  );
}

function SettingsPanel({ readiness, notifications, settings, saveSettings, markNotification, runWorkers }) {
  const checks = readiness.checks || [];
  return (
    <section className="split">
      <Panel title="生产就绪">
        <Rows
          items={checks}
          empty="暂无 readiness 数据。"
          render={(check) => (
            <div className="row-main">
              <span className={`dot ${check.status}`}></span>
              <div>
                <strong>{check.name}</strong>
                <p>{check.message}</p>
              </div>
              <small>{check.status}</small>
            </div>
          )}
        />
      </Panel>
      <Panel title="通知与调度">
        <Rows
          items={notifications.items}
          empty="暂无未读通知。"
          render={(item) => (
            <div className="approval-row">
              <div>
                <strong>{item.title}</strong>
                <p>{item.body || item.severity}</p>
              </div>
              <div className="inline-actions">
                <button data-testid={`notification-${item.id}-read`} onClick={() => markNotification(item.id, "read")}>
                  <Check size={17} />
                  已读
                </button>
                <button data-testid={`notification-${item.id}-archive`} onClick={() => markNotification(item.id, "archived")}>
                  <Archive size={17} />
                  归档
                </button>
              </div>
            </div>
          )}
        />
        <button onClick={runWorkers}>
          <Send size={17} />
          运行调度入口
        </button>
      </Panel>
      <Panel title="卖家设置" span="list">
        <ApiForm testId="settings-form" onSubmit={saveSettings} submitLabel="保存设置" key={settings?.id || "empty"}>
          <Field name="name" label="名称" defaultValue={settings?.name || "Demo Exporter"} required />
          <div className="form-grid">
            <Field name="phone" label="电话" defaultValue={settings?.phone || ""} />
            <Field name="plan" label="方案" defaultValue={settings?.plan || "mvp"} required />
            <Field
              name="large_order_approval_threshold"
              label="大额阈值"
              type="number"
              defaultValue={settings?.settings?.large_order_approval_threshold || "10000"}
            />
          </div>
          <label className="check-field">
            <input name="ai_disclosure" type="checkbox" defaultChecked={settings?.ai_disclosure !== false} />
            <span>AI disclosure</span>
          </label>
        </ApiForm>
      </Panel>
    </section>
  );
}
