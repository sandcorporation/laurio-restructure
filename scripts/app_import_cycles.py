"""백엔드 앱 import 그래프의 강결합 덩어리(순환)를 센다 — #1085, spec #1079.

    python3 scripts/app_import_cycles.py            # 덩어리 크기와 구성
    python3 scripts/app_import_cycles.py --edges    # 덩어리마다 그 안의 앱 → 앱 import 자리(파일:줄)

모듈 최상단(함수·메서드 밖)의 import 만 센다 — 함수 안 import 는 불러올 때 돌지 않아 순환을 만들지 않는다.
`if TYPE_CHECKING:` 아래는 빼고, `tests/`·`migrations/` 는 앱 코드가 아니라 뺀다.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
SKIP_DIRS = {"tests", "migrations", "__pycache__"}
#: 앱이 아니라 프로젝트(설정·주소)다 — 모든 앱을 묶어 올리는 자리라 세면 늘 한 덩어리가 된다
NOT_APPS = {"config"}

Edge = tuple[str, str]
Site = tuple[str, int]


def apps() -> set[str]:
    return {p.name for p in BACKEND.iterdir() if p.is_dir() and (p / "__init__.py").exists() and p.name not in SKIP_DIRS | NOT_APPS}


def _is_type_checking(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def top_level_imports(body: list[ast.stmt]) -> Iterator[ast.Import | ast.ImportFrom]:
    for node in body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            yield node
        elif isinstance(node, ast.If):
            if not _is_type_checking(node.test):
                yield from top_level_imports(node.body)
            yield from top_level_imports(node.orelse)
        elif isinstance(node, ast.Try):
            for block in (node.body, node.orelse, node.finalbody, *(h.body for h in node.handlers)):
                yield from top_level_imports(block)


def targets(node: ast.Import | ast.ImportFrom, own_app: str) -> Iterator[str]:
    if isinstance(node, ast.Import):
        for alias in node.names:
            yield alias.name.split(".")[0]
    elif node.level:  # 상대 import 는 자기 앱
        yield own_app
    elif node.module:
        yield node.module.split(".")[0]


def graph() -> tuple[dict[str, set[str]], dict[Edge, list[Site]]]:
    known = apps()
    deps: dict[str, set[str]] = {app: set() for app in known}
    sites: dict[Edge, list[Site]] = defaultdict(list)
    for app in sorted(known):
        for path in sorted((BACKEND / app).rglob("*.py")):
            if SKIP_DIRS & set(path.relative_to(BACKEND).parts):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in top_level_imports(tree.body):
                for target in targets(node, app):
                    if target in known and target != app:
                        deps[app].add(target)
                        sites[(app, target)].append((str(path.relative_to(BACKEND)), node.lineno))
    return deps, sites


def strongly_connected(deps: dict[str, set[str]]) -> list[list[str]]:
    """Tarjan — 크기 큰 순."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    out: list[list[str]] = []

    def visit(v: str) -> None:
        index[v] = low[v] = len(index)
        stack.append(v)
        on_stack.add(v)
        for w in sorted(deps[v]):
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                comp.append(w)
                if w == v:
                    break
            out.append(sorted(comp))

    sys.setrecursionlimit(10_000)
    for v in sorted(deps):
        if v not in index:
            visit(v)
    return sorted(out, key=lambda c: (-len(c), c))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--edges", action="store_true", help="덩어리마다 그 안의 import 자리")
    args = parser.parse_args()
    deps, sites = graph()
    comps = strongly_connected(deps)
    print(f"앱 {len(deps)}개, 가장 큰 순환 덩어리 {len(comps[0])}개")
    for comp in comps:
        if len(comp) > 1:
            print(f"  [{len(comp)}] {' '.join(comp)}")
    if args.edges:
        for comp in comps:
            if len(comp) < 2:
                continue
            members = set(comp)
            print(f"\n[{len(comp)}] {' '.join(comp)}")
            for (src, dst), where in sorted(sites.items()):
                if src in members and dst in members:
                    print(f"{src} → {dst}: " + ", ".join(f"{f}:{n}" for f, n in where))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
