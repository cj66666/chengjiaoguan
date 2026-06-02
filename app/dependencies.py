from fastapi import Header


def get_seller_id(x_seller_id: int | None = Header(default=1, alias="X-Seller-Id")) -> int:
    return x_seller_id or 1

