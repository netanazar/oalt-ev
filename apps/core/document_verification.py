from __future__ import annotations

import hashlib
import hmac
from decimal import Decimal, InvalidOperation

from django.conf import settings


def _hmac_digest(payload: str) -> str:
    secret = str(settings.SECRET_KEY or "").encode("utf-8")
    return hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest().upper()


def _normalize_amount(value) -> str:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        amount = Decimal("0.00")
    return f"{amount:.2f}"


def invoice_signature(order_number: str, total_amount, issued_ts: int) -> str:
    payload = f"INV|{order_number}|{_normalize_amount(total_amount)}|{int(issued_ts)}"
    return _hmac_digest(payload)[:24]


def warranty_signature(claim_number: str, warranty_card_number: str, order_number: str, issued_ts: int) -> str:
    payload = f"WAR|{claim_number}|{warranty_card_number}|{order_number}|{int(issued_ts)}"
    return _hmac_digest(payload)[:24]

