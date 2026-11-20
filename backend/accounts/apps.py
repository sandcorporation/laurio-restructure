from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Authentication · 계정"

    # 신원 파기 스캔 둘(#102, #138)은 #1086 에서 `verification.apps` 로 옮겼다 — 공유층이 본인확인 기록을 읽지 않는다.
