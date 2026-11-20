"""공모전 앱이 위 층에 묻는 자리 — 위 층 앱이 `AppConfig.ready()` 에서 올린다(#1086, `core.registry` 의 모양).

`payments.Payment` 는 `Contest` 를 FK 로 가리키는 위 층 모델이다. 공모전 API 가 결제 행을 직접 읽으려고
`payments` 를 import 하면 둘이 한 순환이 된다. 그래서 결제 쪽 질의 둘은 `payments.apps` 가 여기에 올린다.
Award(`awards.apps`)와 채점·완성도·가산(`scoring.apps`)도 같은 까닭으로 여기서 받는다 — 둘 다 `ContestSubmission`
을 FK 로 가리키는 위 층이다.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TYPE_CHECKING

from core.registry import Slot

if TYPE_CHECKING:
    from datetime import datetime

    from django.db.models import Q, QuerySet

    from policies.models import PlatformPolicy

    from contests.models import Contest, ContestSubmission, Requirement
    from core.quality_review import BonusScore, QualityTotal
    from scoring.models import SubmissionQualityReview

#: `payments.services.sync_requested_payment_prize` — 진행 중(REQUESTED) 결제의 상금 스냅샷을 지금 상금으로
SYNC_REQUESTED_PAYMENT_PRIZE: Slot[Callable[["Contest"], None]] = Slot("진행 중 결제 상금 맞추기", "payments.apps")

#: `payments.services.has_refunded_payment` — 환불된(REFUNDED) 결제가 있나
HAS_REFUNDED_PAYMENT: Slot[Callable[["Contest"], bool]] = Slot("환불된 결제 있음", "payments.apps")


def sync_requested_payment_prize(contest: Contest) -> None:
    SYNC_REQUESTED_PAYMENT_PRIZE.get()(contest)


def has_refunded_payment(contest: Contest) -> bool:
    return HAS_REFUNDED_PAYMENT.get()(contest)


#: `awards.services.sponsor_user_id_if_awarded` — 이 Contest 에서 이 Developer 가 선정됐으면 Sponsor 의 User pk
AWARDED_SPONSOR_USER_ID: Slot[Callable[[int, int], "int | None"]] = Slot("선정된 제출의 Sponsor", "awards.apps")

#: `awards.services.is_submission_awarded` — 이 제출에 Award 가 있나
IS_SUBMISSION_AWARDED: Slot[Callable[[int], bool]] = Slot("제출 선정 여부", "awards.apps")

#: `scoring.services.upload_source_over_budget` — 올린 소스가 채점 한도를 넘겠나(#989 B)
UPLOAD_SOURCE_OVER_BUDGET: Slot[Callable[["ContestSubmission"], bool]] = Slot("소스 채점 한도 어림", "scoring.apps")

#: `scoring.quality.ranked_reviews` — 제출 id → (완성도 기록, 합계, 순위)
RANKED_REVIEWS: Slot[
    Callable[[int, list[int]], "dict[int, tuple[SubmissionQualityReview, QualityTotal, int]]"]
] = Slot("완성도 순위", "scoring.apps")

#: `scoring.quality.bonus_scores` — 제출 id → 가산 항목마다의 개최자 점수(#905)
BONUS_SCORES: Slot[Callable[[int, list[int]], "dict[int, list[BonusScore]]"]] = Slot("가산 점수", "scoring.apps")

#: `scoring.quality.save_bonus_score` — 가산 하나를 덮어쓴다(#905)
SAVE_BONUS_SCORE: Slot[Callable[[int, "Requirement", int, str, int, "datetime"], None]] = Slot(
    "가산 점수 저장", "scoring.apps"
)


def awarded_sponsor_user_id(contest_id: int, developer_user_id: int) -> int | None:
    return AWARDED_SPONSOR_USER_ID.get()(contest_id, developer_user_id)


def is_submission_awarded(submission_id: int) -> bool:
    return IS_SUBMISSION_AWARDED.get()(submission_id)


def upload_source_over_budget(submission: ContestSubmission) -> bool:
    return UPLOAD_SOURCE_OVER_BUDGET.get()(submission)


def ranked_reviews(
    contest_id: int, submission_ids: list[int]
) -> dict[int, tuple[SubmissionQualityReview, QualityTotal, int]]:
    return RANKED_REVIEWS.get()(contest_id, submission_ids)


def bonus_scores(contest_id: int, submission_ids: list[int]) -> dict[int, list[BonusScore]]:
    return BONUS_SCORES.get()(contest_id, submission_ids)


def save_bonus_score(
    submission_id: int, requirement: Requirement, score: int, memo: str, rated_by_id: int, rated_at: datetime
) -> None:
    SAVE_BONUS_SCORE.get()(submission_id, requirement, score, memo, rated_by_id, rated_at)


#: `scoring.size_hold.size_held_q` — 「지금 크기 초과 보류」 조건(`ScoringAttempt` 를 본다, #986). `contests.scoring_hold` 가 쓴다.
SIZE_HELD_FILTER: Slot[Callable[[], "Q"]] = Slot("크기 초과 보류 조건", "scoring.apps")

#: `scoring.quality.points_by_requirement` — 요구사항 id → 배점. 참가 화면의 완성도 보기가 쓴다.
POINTS_BY_REQUIREMENT: Slot[Callable[[int], "dict[int, int]"]] = Slot("요구사항 배점", "scoring.apps")

#: `awards.api.award_contest_submission` — 연결된 앱(MCP)의 「선정」이 화면 API 와 같은 길을 탄다(#870).
AWARD_SUBMISSION: Slot[Callable[["Contest", int], None]] = Slot("제출 선정", "awards.apps")


class SponsoredContestQuerySet(Protocol):
    def __call__(self, base: "QuerySet[Contest]", *, as_of: "datetime", policy: "PlatformPolicy") -> "QuerySet[Contest]": ...


#: `payouts.sponsor_contests.sponsored_contest_queryset` — 개최자 목록이 행마다 판정할 사실(채점·이의·지급·배분)을 붙인다(#81).
SPONSORED_CONTEST_QUERYSET: Slot[SponsoredContestQuerySet] = Slot("개최자 목록 사실 붙이기", "payouts.apps")

#: `payouts.participation.payout_action` — 참가자 화면의 돈 걸린 단계(#130, #177). None 이면 지급 단계가 아니다.
PAYOUT_ACTION: Slot[Callable[["ContestSubmission"], "str | None"]] = Slot("참가자 지급 단계", "payouts.apps")
