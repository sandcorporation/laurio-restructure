"""공모전 앱이 위 층에 묻는 자리 — 위 층 앱이 `AppConfig.ready()` 에서 올린다(#1086, `core.registry` 의 모양).

`payments.Payment` 는 `Contest` 를 FK 로 가리키는 위 층 모델이다. 공모전 API 가 결제 행을 직접 읽으려고
`payments` 를 import 하면 둘이 한 순환이 된다. 그래서 결제 쪽 질의 둘은 `payments.apps` 가 여기에 올린다.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from core.registry import Slot

if TYPE_CHECKING:
    from contests.models import Contest

#: `payments.services.sync_requested_payment_prize` — 진행 중(REQUESTED) 결제의 상금 스냅샷을 지금 상금으로
SYNC_REQUESTED_PAYMENT_PRIZE: Slot[Callable[["Contest"], None]] = Slot("진행 중 결제 상금 맞추기", "payments.apps")

#: `payments.services.has_refunded_payment` — 환불된(REFUNDED) 결제가 있나
HAS_REFUNDED_PAYMENT: Slot[Callable[["Contest"], bool]] = Slot("환불된 결제 있음", "payments.apps")


def sync_requested_payment_prize(contest: Contest) -> None:
    SYNC_REQUESTED_PAYMENT_PRIZE.get()(contest)


def has_refunded_payment(contest: Contest) -> bool:
    return HAS_REFUNDED_PAYMENT.get()(contest)
