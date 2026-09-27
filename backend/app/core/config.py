import os
from pathlib import Path
from pydantic import BaseModel, Field

class Settings(BaseModel):
    PROJECT_NAME: str = "AI Application Reliability & Predictive QA Platform"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Base directories
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = Path(__file__).resolve().parent.parent.parent / "data"
    REPORTS_DIR: Path = Path(__file__).resolve().parent.parent.parent / "reports"
    
    # Database
    DATABASE_PATH: str = str(Path(__file__).resolve().parent.parent.parent / "data" / "reliability_platform.db")
    
    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*",
    ]
    
    # LLM Settings (for future Ollama integration)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "qwen2.5-coder:7b")

settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
