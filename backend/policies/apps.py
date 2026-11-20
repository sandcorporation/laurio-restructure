from django.apps import AppConfig


class PoliciesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "policies"
    verbose_name = "PlatformPolicy · 정책값"

    def ready(self) -> None:
        # core 가 운영 설정을 import 없이 부르는 자리(#1086) — `core.runtime_settings_port`
        from core.runtime_settings_port import RUNTIME_SETTINGS
        from policies import runtime_settings

        RUNTIME_SETTINGS.register(runtime_settings)
