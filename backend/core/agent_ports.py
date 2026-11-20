"""공유층이 기능 앱에 기대던 자리 — 기능 앱이 `AppConfig.ready()` 에서 제 구현을 등록한다(#1085, spec #1079 결정 4).

공유층(`core`)이 기능 앱을 최상단에서 import 하면 앱 import 그래프가 한 순환으로 묶인다. 그래서 방향을 뒤집어
기능 앱이 여기에 올리고, 공유층은 부를 때 여기서 꺼낸다. 등록하기 전에 부르면 `PortNotRegistered` 로 멈춘다 —
조용히 비켜 가지 않는다(Django 가 뜨면 `ready()` 가 늘 먼저 돈다: 웹·celery·`manage.py llm_proxy` 모두).

| 자리 | 쓰는 곳 | 올리는 곳 |
| --- | --- | --- |
| 에이전트 채점 실행기 계약(`scoring.agent_runner` 모듈 그대로) | `core.agent_scoring`, `classroom.agent_grading` | `scoring.apps` |
| 클래스 키 풀기(`classroom.scoring_connection.agent_vendor_key`) | `core.llm_proxy` | `classroom.apps` |
| 모델 단가(`classroom.scoring_cost.price_for`) | `core.agent_run_tokens` | `classroom.apps` |

실행기 계약의 타입(`Vendor`·`RunSpec`·`RunResult`)은 `scoring.agent_runner` 의 것과 같은 모양을 여기 둔다 — 실행기
파일은 이미지가 홀로 COPY 하는 표준 라이브러리 모듈이라 이 모듈을 import 할 수 없다. 둘이 같은지는
`tests/test_agent_ports.py` 가 견준다.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, NotRequired, Protocol, TypedDict

Vendor = Literal["anthropic", "openai"]


class RunSpec(TypedDict):
    """실행 하나의 요청 — `scoring.agent_runner.RunSpec` 과 같은 모양."""

    vendor: Vendor
    model: str
    prompt: str
    output_schema: dict[str, object]
    run_token: str
    max_budget_usd: float
    timeout_seconds: NotRequired[int]


class RunResult(TypedDict):
    """실행 하나의 결과 — `scoring.agent_runner.RunResult` 와 같은 모양."""

    run_id: str
    vendor: Vendor
    cli_version: str
    exit_code: int | None
    timed_out: bool
    duration_seconds: float
    repo_root_prefix: str
    stdout: str
    stdout_truncated: bool
    stderr_tail: str


class AgentGrader(Protocol):
    """실행기 계약 — `scoring.agent_runner` 모듈이 그대로 이 모양이다(오류 클래스는 그 모듈의 것을 그대로 잡는다)."""

    CLAUDE_TOOLS: tuple[str, ...]
    AgentGraderBusy: type[Exception]
    AgentGraderError: type[Exception]
    RunRejected: type[Exception]

    def request_run(self, spec: RunSpec, repo_zip: bytes, *, timeout: float) -> RunResult: ...


class ModelPrice(Protocol):
    """모델 단가(USD / 100만 토큰) — `classroom.scoring_cost.ModelPrice` 가 이 모양이다."""

    @property
    def input_usd_per_million(self) -> float: ...
    @property
    def output_usd_per_million(self) -> float: ...
    @property
    def long_context_input_tokens(self) -> int | None: ...
    @property
    def long_context_input_multiplier(self) -> float: ...
    @property
    def long_context_output_multiplier(self) -> float: ...


ClassVendorKey = Callable[[int, str], str]
PriceFor = Callable[[str], ModelPrice | None]


class PortNotRegistered(RuntimeError):
    """기능 앱이 아직 올리지 않은 자리를 불렀다 — 그 앱이 INSTALLED_APPS 에 없거나 Django 가 뜨기 전이다."""


_agent_grader: AgentGrader | None = None
_class_vendor_key: ClassVendorKey | None = None
_price_for: PriceFor | None = None


def register_agent_grader(grader: AgentGrader) -> None:
    global _agent_grader
    _agent_grader = grader


def agent_grader() -> AgentGrader:
    if _agent_grader is None:
        raise PortNotRegistered("에이전트 채점 실행기가 등록되지 않았다(scoring.apps)")
    return _agent_grader


def register_class_vendor_key(fn: ClassVendorKey) -> None:
    global _class_vendor_key
    _class_vendor_key = fn


def class_vendor_key(class_id: int, vendor: str) -> str:
    if _class_vendor_key is None:
        raise PortNotRegistered("클래스 키 풀기가 등록되지 않았다(classroom.apps)")
    return _class_vendor_key(class_id, vendor)


def register_price_for(fn: PriceFor) -> None:
    global _price_for
    _price_for = fn


def price_for(model_id: str) -> ModelPrice | None:
    if _price_for is None:
        raise PortNotRegistered("모델 단가표가 등록되지 않았다(classroom.apps)")
    return _price_for(model_id)
