from __future__ import annotations

from django.apps import AppConfig


class AwardsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "awards"
    verbose_name = "Award · 선정"

    def ready(self) -> None:
        # 공모전 앱이 묻는 선정 질의 둘(#1086) — `contests.ports`
        from contests.ports import AWARDED_SPONSOR_USER_ID, IS_SUBMISSION_AWARDED

        from .services import is_submission_awarded, sponsor_user_id_if_awarded

        AWARDED_SPONSOR_USER_ID.register(sponsor_user_id_if_awarded)
        IS_SUBMISSION_AWARDED.register(is_submission_awarded)
