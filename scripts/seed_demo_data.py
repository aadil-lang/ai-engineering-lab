import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.models.target import ApplicationTarget
from backend.app.services.target_service import TargetService
from backend.app.services.test_case_service import TestCaseService
from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.core.config import settings

def seed_data():
    print("[AI Reliability Platform] Seeding demo applications & test suites...")
    repo = SQLiteRepository(settings.DATABASE_PATH)
    target_service = TargetService(repo)
    test_case_service = TestCaseService(repo)

    # Seed targets from JSON file
    targets_file = Path(__file__).resolve().parent.parent / "data" / "default_targets.json"
    if targets_file.exists():
        with open(targets_file, "r", encoding="utf-8") as f:
            targets_raw = json.load(f)
            for t_data in targets_raw:
                target = ApplicationTarget(**t_data)
                repo.create_target(target)
                print(f"  -> Seeded Target: {target.name} ({target.target_id})")

    # Seed test suites
    test_case_service.list_test_cases()
    print("  -> Seeded 5 standard Test Suites (Functional, Exploratory, UX/UI, AI/LLM, Regression).")
    print("[AI Reliability Platform] Seeding completed successfully.")

if __name__ == "__main__":
    seed_data()
