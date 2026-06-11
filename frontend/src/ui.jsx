/**
 * [INPUT]: 依赖 React JSX 与 lucide-react Plus 图标
 * [OUTPUT]: 对外提供 Panel、Rows、StatusRows、ApiForm、Field、JsonField、Metric、IconButton、CodeBlock
 * [POS]: frontend/src 的通用 UI 基元层，承载标题副文案、右侧动作与 KPI delta 等设计稿通用结构
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */

import { BarChart3, Plus } from "lucide-react";

export function Panel({ title, subtitle, action, children, span = "" }) {
  return (
    <section className={`panel card card-pad ${span}`}>
      <header>
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {action && <div className="panel-action">{action}</div>}
      </header>
      {children}
    </section>
  );
}

export function Rows({ items = [], empty, render }) {
  if (!items.length) return <p className="empty">{empty}</p>;
  return <div className="rows">{items.map((item) => <div className="row" key={item.id || item.name || item.title}>{render(item)}</div>)}</div>;
}

export function StatusRows({ rows = [], empty = "暂无数据。" }) {
  if (!rows.length) return <p className="empty">{empty}</p>;
  return <div className="status-rows">{rows.map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>;
}

export function ApiForm({ children, submitLabel, onSubmit, testId }) {
  return (
    <form
      className="api-form"
      data-testid={testId}
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(new FormData(event.currentTarget));
      }}
    >
      {children}
      <button className="btn btn-pri primary" type="submit" data-testid={testId ? `${testId}-submit` : undefined}>
        <Plus size={17} />
        {submitLabel}
      </button>
    </form>
  );
}

export function Field({ label, name, type = "text", ...props }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input name={name} type={type} {...props} />
    </label>
  );
}

export function JsonField({ label, name, defaultValue }) {
  return (
    <label className="field">
      <span>{label}</span>
      <textarea name={name} defaultValue={JSON.stringify(defaultValue, null, 2)} rows={4} />
    </label>
  );
}

function MetricSpark({ color }) {
  const points = "0,22 16,17 31,24 47,10 64,16 88,7";
  return (
    <svg className="metric-spark" viewBox="0 0 88 30" aria-hidden="true">
      <polyline points={points} fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="88" cy="7" r="2.8" fill="#fff" stroke={color} strokeWidth="2" />
    </svg>
  );
}

export function Metric({ label, value, tone = "blue", delta, onClick, testId, icon: Icon = BarChart3, alert = false }) {
  const Component = onClick ? "button" : "div";
  const toneColor = {
    blue: "var(--primary)",
    amber: "var(--orange)",
    green: "var(--green)",
    teal: "var(--green)",
    red: "var(--red)",
  }[tone] || "var(--primary)";
  return (
    <Component
      className={`metric ${tone}${onClick ? " metric-button" : ""}`}
      type={onClick ? "button" : undefined}
      onClick={onClick}
      data-testid={testId}
      aria-label={onClick ? `${label} ${value}` : undefined}
    >
      {alert && <i className="metric-alert" aria-hidden="true" />}
      <span className="metric-head">
        <span className="metric-icon">
          <Icon size={18} />
        </span>
        <span>{label}</span>
      </span>
      <span className="metric-body">
        <span className="metric-value">
          <strong>{value}</strong>
          {delta && <em>{delta}</em>}
        </span>
        <MetricSpark color={toneColor} />
      </span>
    </Component>
  );
}

export function IconButton({ label, icon: Icon, ...props }) {
  return (
    <button className="btn-icon btn-sec icon-button" aria-label={label} title={label} {...props}>
      <Icon size={18} />
    </button>
  );
}

export function CodeBlock({ value }) {
  return <pre>{JSON.stringify(value, null, 2)}</pre>;
}
