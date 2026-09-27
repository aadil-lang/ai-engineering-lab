from pydantic import BaseModel, Field
import uuid

class Environment(BaseModel):
    environment_id: str = Field(default_factory=lambda: f"env_{uuid.uuid4().hex[:8]}")
    name: str = "Local Test Environment"
    browser: str = "Chromium (Headless)"
    os: str = "Windows 11 / x86_64"
    viewport: str = "1920x1080"
    network_profile: str = "Broadband (100Mbps)"
    env_vars: dict[str, str] = Field(default_factory=dict)
