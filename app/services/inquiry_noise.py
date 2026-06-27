"""
/* ========================================================================== */
/* GEB L3: 非询价邮件噪声规则                                                 */
/* ========================================================================== */
/**
 * [INPUT]: 依赖 SQLAlchemy expression helpers
 * [OUTPUT]: 对外提供系统发件人与非询价内容的 SQL 条件 helper
 * [POS]: services 的轻量噪声识别边界，避免系统通知/退信抢占 Agent 与审批演示主线
 * [PROTOCOL]: 变更时同步更新 worker、审批与询盘相关测试
 */
"""

from sqlalchemy import case, or_


SYSTEM_SENDER_KEYWORDS = (
    "mailer-daemon",
    "postmaster",
    "no-reply",
    "noreply",
    "googlecommunityteam",
    "google-gemini",
)
NON_INQUIRY_KEYWORDS = (
    "delivery incomplete",
    "message not delivered",
    "delivery status notification",
    "2-step verification",
    "welcome to google",
    "authenticator app",
    "recovery email",
    "otp code",
    "your otp",
    "lotte cinema",
    "movie ticket",
)


def not_ilike_any(column, keywords: tuple[str, ...]) -> list:
    return [or_(column.is_(None), ~column.ilike(f"%{keyword}%")) for keyword in keywords]


def noise_rank(email_column, content_column):
    sender_noise = [email_column.ilike(f"%{keyword}%") for keyword in SYSTEM_SENDER_KEYWORDS]
    content_noise = [content_column.ilike(f"%{keyword}%") for keyword in NON_INQUIRY_KEYWORDS]
    return case((or_(*sender_noise, *content_noise), 1), else_=0)
