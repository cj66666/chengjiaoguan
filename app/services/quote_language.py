from app.services.quote_engine import QuoteResult


def render_quote_message(result: QuoteResult) -> str:
    lines = [
        f"Thanks for your inquiry. Here is our quote in {result.currency}:",
    ]
    for line in result.lines:
        lines.append(
            f"- Product #{line.product_id}: {line.quantity} pcs x {result.currency} {line.unit_price} = {result.currency} {line.amount}"
        )
    lines.append(f"Total: {result.currency} {result.total_amount}. Valid until {result.valid_until.isoformat()}.")
    if result.hits_floor:
        lines.append("This quote requires human approval because it is below the configured floor price.")
    return "\n".join(lines)

