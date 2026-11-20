"""e2e 계획(scripts/ci/e2e_plan.py, #1089) — 폴더 이름이 앱 표시이고, 바뀐 파일이 맞는 조각을 고른다."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "ci"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import e2e_plan  # noqa: E402
from app_deps import load_table  # noqa: E402

TABLE = load_table()


def picked(*changed: str) -> set[str]:
    return {p for shard in e2e_plan.plan(list(changed))["include"] for p in shard["paths"].split()}


class FolderNamesAreAppMarks(unittest.TestCase):
    def test_every_folder_is_a_declared_app_or_frontend(self) -> None:
        for project, apps in e2e_plan.folders().items():
            for app in apps:
                self.assertIn(app, {*TABLE, e2e_plan.PSEUDO_APP}, f"{project}: e2e 폴더 {app} 는 app_deps.toml 의 앱도 frontend 도 아니다")

    def test_no_spec_sits_outside_an_app_folder(self) -> None:
        for spec in e2e_plan.E2E.glob("*.spec.ts"):
            self.fail(f"{spec.name} — 시험은 앱 폴더 안에 둔다")
        for spec in (e2e_plan.E2E / "operator").glob("*.spec.ts"):
            self.fail(f"operator/{spec.name} — 시험은 앱 폴더 안에 둔다")


class Selection(unittest.TestCase):
    def test_docs_only_runs_nothing(self) -> None:
        self.assertEqual(picked("docs/ops/ci.md"), set())

    def test_backend_app_runs_its_folders_and_users(self) -> None:
        got = picked("backend/payments/api.py")
        self.assertTrue(any(f.startswith("e2e/payments/") for f in got))
        self.assertFalse(any(f.startswith("e2e/frontend/") for f in got))

    def test_unattributed_backend_file_runs_everything(self) -> None:
        self.assertEqual(picked("backend/config/settings.py"), picked("scripts/ci/e2e.sh"))

    def test_classroom_front_runs_only_classroom(self) -> None:
        got = picked("classroom/app/page.tsx")
        self.assertTrue(got and all(f.startswith("e2e/classroom/") for f in got))

    def test_a_spec_folder_change_runs_that_folder(self) -> None:
        got = picked("frontend/e2e/contests/contests-list.spec.ts")
        self.assertTrue(got and all(f.startswith("e2e/contests/") for f in got))

    def test_shared_helper_runs_everything(self) -> None:
        self.assertEqual(picked("frontend/e2e/lib/seed.ts"), picked("scripts/ci/e2e.sh"))

    def test_all_covers_every_spec_once(self) -> None:
        shards = e2e_plan.plan(None)["include"]
        files = [f for s in shards for f in s["paths"].split()]
        self.assertEqual(len(files), len(set(files)))
        self.assertEqual(len(files), sum(len(v) for apps in e2e_plan.folders().values() for v in apps.values()))


if __name__ == "__main__":
    unittest.main()
