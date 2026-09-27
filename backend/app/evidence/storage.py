from pathlib import Path
import json
from backend.app.core.config import settings

class LocalEvidenceBlobStorage:
    """
    Handles structured persistence of artifacts on disk:
    artifacts/{run_id}/screenshots/
    artifacts/{run_id}/dom/
    artifacts/{run_id}/network/
    artifacts/{run_id}/console/
    artifacts/{run_id}/performance/
    """
    def __init__(self, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir) if base_dir else settings.DATA_DIR / "artifacts"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_run_dir(self, run_id: str, subfolder: str | None = None) -> Path:
        run_folder = self.base_dir / run_id
        if subfolder:
            target_dir = run_folder / subfolder
        else:
            target_dir = run_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def store_screenshot(self, run_id: str, evidence_id: str, image_bytes: bytes) -> str:
        folder = self.get_run_dir(run_id, "screenshots")
        file_path = folder / f"{evidence_id}.png"
        file_path.write_bytes(image_bytes)
        return str(file_path)

    def store_dom_snapshot(self, run_id: str, evidence_id: str, html_content: str) -> str:
        folder = self.get_run_dir(run_id, "dom")
        file_path = folder / f"{evidence_id}.html"
        file_path.write_text(html_content, encoding="utf-8")
        return str(file_path)

    def store_network_data(self, run_id: str, evidence_id: str, har_data: dict | list) -> str:
        folder = self.get_run_dir(run_id, "network")
        file_path = folder / f"{evidence_id}.json"
        file_path.write_text(json.dumps(har_data, indent=2), encoding="utf-8")
        return str(file_path)

    def store_console_logs(self, run_id: str, evidence_id: str, logs: list) -> str:
        folder = self.get_run_dir(run_id, "console")
        file_path = folder / f"{evidence_id}.json"
        file_path.write_text(json.dumps(logs, indent=2), encoding="utf-8")
        return str(file_path)

    def store_performance_data(self, run_id: str, evidence_id: str, perf_data: dict) -> str:
        folder = self.get_run_dir(run_id, "performance")
        file_path = folder / f"{evidence_id}.json"
        file_path.write_text(json.dumps(perf_data, indent=2), encoding="utf-8")
        return str(file_path)

    def store_generic_blob(self, run_id: str, subfolder: str, evidence_id: str, extension: str, content: bytes | str) -> str:
        folder = self.get_run_dir(run_id, subfolder)
        file_path = folder / f"{evidence_id}.{extension}"
        if isinstance(content, str):
            file_path.write_text(content, encoding="utf-8")
        else:
            file_path.write_bytes(content)
        return str(file_path)

    def retrieve_blob(self, file_path_str: str) -> bytes | None:
        p = Path(file_path_str)
        if p.exists() and p.is_file():
            return p.read_bytes()
        return None
