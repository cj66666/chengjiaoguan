/**
 * [INPUT]: 依赖浏览器 FormData
 * [OUTPUT]: 对外提供 safeGet、productPayload、pricingPayload、channelPayload、testDeliveryPayload、settingsPayload
 * [POS]: frontend/src 的表单归一层，把 UI 表单值折叠成后端 schema 接受的最小 payload
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */

export async function safeGet(api, path, fallback) {
  try {
    return await api.get(path);
  } catch {
    return fallback;
  }
}

export function productPayload(form) {
  return compact({
    name: text(form, "name"),
    sku: text(form, "sku"),
    cost: text(form, "cost"),
    currency: text(form, "currency") || "USD",
    moq: numberValue(form, "moq"),
    description: text(form, "description"),
    specs: jsonValue(form, "specs", {}),
  });
}

export function pricingPayload(form) {
  return compact({
    product_id: numberValue(form, "product_id"),
    margin_rate: text(form, "margin_rate"),
    logistics_template: jsonValue(form, "logistics_template", {}),
    tiered_prices: jsonValue(form, "tiered_prices", []),
    valid_days: numberValue(form, "valid_days"),
    floor_price: text(form, "floor_price"),
    currency: text(form, "currency") || "USD",
  });
}

export function channelPayload(form) {
  return compact({
    channel_type: text(form, "channel_type"),
    name: text(form, "name"),
    credentials: channelCredentials(form),
    status: "connected",
  });
}

export function settingsPayload(form) {
  return compact({
    name: text(form, "name"),
    phone: text(form, "phone"),
    plan: text(form, "plan"),
    ai_disclosure: form.get("ai_disclosure") === "on",
    settings: compact({
      large_order_approval_threshold: text(form, "large_order_approval_threshold"),
    }),
  });
}

function jsonValue(form, name, fallback) {
  const raw = text(form, name);
  if (!raw) return fallback;
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`${name} JSON 无效: ${error.message}`);
  }
}

export function testDeliveryPayload(form) {
  return compact({
    to: text(form, "to"),
    subject: text(form, "subject"),
    body: text(form, "body"),
    confirm_live: false,
  });
}

function channelCredentials(form) {
  const raw = text(form, "credentials");
  if (raw) return jsonValue(form, "credentials", {});
  const channelType = text(form, "channel_type");
  if (channelType === "email") {
    return compact({
      imap_host: text(form, "imap_host"),
      imap_port: numberValue(form, "imap_port") || 993,
      smtp_host: text(form, "smtp_host"),
      smtp_port: numberValue(form, "smtp_port") || 465,
      username: text(form, "username"),
      password: text(form, "password"),
      mailbox: text(form, "mailbox") || "INBOX",
      poll_enabled: form.get("poll_enabled") === "on",
      use_ssl: form.get("use_ssl") !== "off",
    });
  }
  if (channelType === "whatsapp") {
    return compact({
      access_token: text(form, "access_token"),
      phone_number_id: text(form, "phone_number_id"),
      api_version: text(form, "api_version") || "v20.0",
    });
  }
  return {};
}

function text(form, name) {
  const value = form.get(name);
  return typeof value === "string" ? value.trim() : "";
}

function numberValue(form, name) {
  const value = text(form, name);
  return value ? Number(value) : undefined;
}

function compact(value) {
  return Object.fromEntries(Object.entries(value).filter(([, entry]) => entry !== "" && entry !== undefined && entry !== null));
}
