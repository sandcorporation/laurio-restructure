"""e2e 를 무엇을, 몇 조각으로 돌지 — 바뀐 파일 → 앱 폴더 → 조각(#1089, spec #1079).

    python3 scripts/ci/e2e_plan.py --base <기준 커밋>   # PR: 바뀐 앱의 시험만
    python3 scripts/ci/e2e_plan.py --all                # 매시 main(e2e.yml): 전부 — 병합 대기열은 e2e 를 돌지 않는다(#1111)

시험 파일은 `frontend/e2e/<앱>/`(공개), `frontend/e2e/operator/<앱>/`(운영자), `frontend/e2e/classroom/`(강의실, 앱 `classroom`)에
둔다. 폴더 이름이 앱 표시다 — `backend/app_deps.toml` 의 앱 이름이거나 `frontend`(백엔드 앱이 없는 화면·BFF 시험).
`backend/**/tests/**` 는 e2e 를 고르지 않는다(#1110). 바뀐 백엔드 앱 → `scripts/app_deps.py` 의 `affected` 가 고른 앱들의 폴더. 앞단(frontend/·operator/·classroom/)이 바뀌면 그
앱의 시험 전부, 시험 폴더만 바뀌면 그 폴더만, 그 밖(공유 시험 도우미·설정·워크플로·packages·루트)은 전부.

출력(줄마다 `KEY=값`): `E2E=0|1`, `MATRIX={"include":[{"name","project","paths"}…]}`. 폴더는 시험 수로 조각에 나눠 담는다
(`SHARD_TESTS` 개 안팎) — 조각마다 실행기가 하나라 나란히 돈다.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app_deps import affected, load_table  # noqa: E402
from paths import kind  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
E2E = ROOT / "frontend" / "e2e"
PSEUDO_APP = "frontend"  # 백엔드 앱이 없는 시험 — 앞단이 바뀔 때만 돈다
SHARD_TESTS = 40
TEST_CALL = re.compile(r"^\s*test(?:\.[a-z]+)*\(", re.MULTILINE)



def folders() -> dict[str, dict[str, dict[str, int]]]:
    """project → {앱: {시험 파일(frontend 기준): 시험 수}}. 시험 파일이 있는 폴더만."""

    out: dict[str, dict[str, dict[str, int]]] = {"public": {}, "operator": {}, "classroom": {}}
    for spec in sorted(E2E.rglob("*.spec.ts")):
        rel = spec.relative_to(E2E).parts
        count = len(TEST_CALL.findall(spec.read_text(encoding="utf-8")))
        project, app = ("classroom", "classroom") if rel[0] == "classroom" else ("operator", rel[1]) if rel[0] == "operator" else ("public", rel[0])
        out[project].setdefault(app, {})[spec.relative_to(ROOT / "frontend").as_posix()] = count
    return out


def select(changed: list[str], table: dict, present: dict[str, dict[str, dict[str, int]]]) -> dict[str, set[str]]:
    """바뀐 파일 → project → 돌 앱 폴더 집합."""

    everything = {p: set(apps) for p, apps in present.items()}
    picked: dict[str, set[str]] = {p: set() for p in present}
    backend: list[str] = []
    for f in changed:
        if kind(f) == "docs":
            continue
        if kind(f) == "backend":
            if "tests" not in f.split("/")[1:-1]:  # 백엔드 시험 파일은 화면 시험이 기대지 않는다 — 건너뛴다
                backend.append(f)
        elif f.startswith("frontend/e2e/classroom/") and not f.startswith("frontend/e2e/classroom/lib/"):
            picked["classroom"].add("classroom")
        elif f.startswith("frontend/e2e/operator/"):
            rest = f.split("/")[3:]
            if len(rest) > 1 and rest[0] in present["operator"]:
                picked["operator"].add(rest[0])
            else:
                return everything
        elif f.startswith("frontend/e2e/") and f.count("/") >= 3 and f.split("/")[2] in present["public"]:
            picked["public"].add(f.split("/")[2])
        elif f.startswith("frontend/") and not f.startswith("frontend/e2e/"):
            picked["public"] |= everything["public"]
        elif f.startswith("operator/"):
            picked["operator"] |= everything["operator"]
        elif f.startswith("classroom/"):
            picked["classroom"] |= everything["classroom"]
        else:  # 공유 시험 도우미·설정·워크플로·packages·루트
            return everything
    if backend:
        apps = affected(backend, table)
        if apps is None:
            return everything
        for project, names in present.items():
            picked[project] |= {a for a in names if a in apps}
    return picked


def shards(project: str, apps: dict[str, dict[str, int]], chosen: set[str]) -> list[dict[str, str]]:
    """고른 폴더의 시험 파일을 시험 수 SHARD_TESTS 안팎의 조각에 나눠 담는다(큰 것부터 가장 가벼운 조각에)."""

    todo = sorted(((n, f) for a in chosen for f, n in apps[a].items()), reverse=True)
    if not todo:
        return []
    count = max(1, round(sum(n for n, _ in todo) / SHARD_TESTS))
    bins: list[tuple[int, list[str]]] = [(0, []) for _ in range(count)]
    for n, spec in todo:
        i = min(range(count), key=lambda k: bins[k][0])
        bins[i] = (bins[i][0] + n, bins[i][1] + [spec])
    return [
        {"name": f"{project}-{i + 1}", "project": project, "paths": " ".join(sorted(files))}
        for i, (_, files) in enumerate(b for b in bins if b[1])
    ]


def plan(changed: list[str] | None) -> dict:
    present = folders()
    if changed is None:
        chosen = {p: set(apps) for p, apps in present.items()}
    else:
        chosen = select(changed, load_table(), present)
    include: list[dict[str, str]] = []
    for project in ("public", "operator", "classroom"):
        include += shards(project, present[project], chosen[project])
    return {"include": include}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", help="기준 커밋 — 이 뒤로 바뀐 파일만 본다")
    parser.add_argument("--all", action="store_true", help="전부(매시 main, e2e.yml)")
    args = parser.parse_args()
    if args.all or not args.base:
        matrix = plan(None)
    else:
        diff = subprocess.run(["git", "diff", "--name-only", args.base, "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True)
        matrix = plan(diff.stdout.split())
    print(f"E2E={1 if matrix['include'] else 0}")
    print("MATRIX=" + json.dumps(matrix, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
