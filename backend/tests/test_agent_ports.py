"""공유층이 기능 앱에 기대던 자리를 기능 앱이 등록한다(#1085) — 등록이 실제로 걸리는가, 계약 모양이 실행 틀과 같은가."""

from __future__ import annotations

from typing import get_type_hints

import pytest

from classroom import scoring_connection, scoring_cost
from classroom.submission_target_state import resolve_classroom_submission
from contests.submission_target_state import resolve_contest_submission
from core import agent_ports
from scoring import agent_runner
from submissions import resolvers


def test_django_setup_registers_every_port_with_the_feature_app_implementation() -> None:
    assert agent_ports.agent_grader() is agent_runner
    assert agent_ports._class_vendor_key is scoring_connection.agent_vendor_key
    assert agent_ports._price_for is scoring_cost.price_for
    assert resolvers._TARGET_SHAPES == {
        "submission": resolve_contest_submission,
        "classroom-submission": resolve_classroom_submission,
    }


def test_price_for_answers_like_the_classroom_table() -> None:
    model = next(iter(scoring_cost.PRICES))
    assert agent_ports.price_for(model) is scoring_cost.price_for(model)
    assert agent_ports.price_for("모르는-모델") is None


@pytest.mark.parametrize("name", ["RunSpec", "RunResult"])
def test_contract_types_match_the_runner_file(name: str) -> None:
    # 실행 틀은 이미지가 홀로 COPY 하는 파일이라 core 를 import 할 수 없다 — 같은 모양을 두 곳에 두고 여기서 견준다.
    ours, theirs = getattr(agent_ports, name), getattr(agent_runner, name)
    assert get_type_hints(ours) == get_type_hints(theirs)
    assert ours.__required_keys__ == theirs.__required_keys__
    assert ours.__optional_keys__ == theirs.__optional_keys__


def test_vendor_literal_matches_the_runner_file() -> None:
    assert agent_ports.Vendor == agent_runner.Vendor


@pytest.mark.parametrize(
    ("attr", "call"),
    [
        ("_agent_grader", agent_ports.agent_grader),
        ("_class_vendor_key", lambda: agent_ports.class_vendor_key(1, "anthropic")),
        ("_price_for", lambda: agent_ports.price_for("gpt-5")),
    ],
)
def test_unregistered_port_stops_instead_of_passing_quietly(monkeypatch: pytest.MonkeyPatch, attr: str, call) -> None:  # noqa: ANN001 - 인자 없는 호출 하나
    monkeypatch.setattr(agent_ports, attr, None)
    with pytest.raises(agent_ports.PortNotRegistered):
        call()


def test_unregistered_target_shape_is_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(resolvers, "_TARGET_SHAPES", {})
    assert resolvers.SubmissionTargetStateResolver().resolve("submission:1:2:source") == resolvers.DENY_TARGET
