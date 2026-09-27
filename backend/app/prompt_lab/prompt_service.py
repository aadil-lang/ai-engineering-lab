import re
import uuid
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone

from backend.app.prompt_lab.models import (
    PromptDefinition,
    PromptVersion,
    PromptStatus,
    StructuredPromptComponents,
)
from backend.app.prompt_lab.repository import PromptLabRepository
from backend.app.prompt_lab.errors import (
    PromptNotFoundError,
    PromptVersionNotFoundError,
    PromptVersionImmutableError,
    InvalidPromptTemplateError,
)


def redact_secrets(text: str) -> str:
    """Safely scrubs potential API tokens, credentials, or keys from strings."""
    if not text:
        return text
    scrubbed = re.sub(r"(ghp_[a-zA-Z0-9]{20,}|github_pat_[a-zA-Z0-9_]{20,}|sk-[a-zA-Z0-9]{20,})", "[REDACTED_SECRET]", text)
    scrubbed = re.sub(r"(Bearer\s+)[a-zA-Z0-9_\-\.]{20,}", r"\1[REDACTED_SECRET]", scrubbed)
    return scrubbed


class PromptService:
    """
    Manages prompt definitions, immutable prompt versions, template validation,
    and secret-scrubbed prompt rendering.
    """

    def __init__(self, repo: Optional[PromptLabRepository] = None):
        self.repo = repo or PromptLabRepository()

    def create_prompt(self, prompt_id: str, name: str, description: str = "") -> PromptDefinition:
        p = PromptDefinition(prompt_id=prompt_id, name=name, description=description)
        return self.repo.save_prompt(p)

    def get_prompt(self, prompt_id: str) -> PromptDefinition:
        p = self.repo.get_prompt(prompt_id)
        if not p:
            raise PromptNotFoundError(f"Prompt '{prompt_id}' does not exist.")
        return p

    def list_prompts(self) -> List[PromptDefinition]:
        return self.repo.list_prompts()

    def create_prompt_version(
        self,
        prompt_id: str,
        template: str,
        variables_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        components: Optional[StructuredPromptComponents] = None,
        change_reason: Optional[str] = None,
        parent_version: Optional[int] = None,
        status: PromptStatus = PromptStatus.DRAFT,
    ) -> PromptVersion:
        # Verify prompt definition exists
        self.get_prompt(prompt_id)

        # Determine next version number
        existing_versions = self.repo.list_prompt_versions(prompt_id)
        next_version = (max(v.version for v in existing_versions) + 1) if existing_versions else 1

        # Basic template syntax check: unclosed brackets
        if template.count("{{") != template.count("}}"):
            raise InvalidPromptTemplateError("Prompt template contains mismatched '{{' and '}}' delimiters.")

        pv = PromptVersion(
            prompt_id=prompt_id,
            version=next_version,
            template=template,
            variables_schema=variables_schema or {},
            output_schema=output_schema,
            components=components,
            parent_version=parent_version or (existing_versions[-1].version if existing_versions else None),
            change_reason=change_reason,
            status=status,
            is_evaluated=False,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return self.repo.save_prompt_version(pv)

    def get_prompt_version(self, prompt_id: str, version: int) -> PromptVersion:
        pv = self.repo.get_prompt_version(prompt_id, version)
        if not pv:
            raise PromptVersionNotFoundError(f"Prompt version {prompt_id}:v{version} does not exist.")
        return pv

    def list_prompt_versions(self, prompt_id: str) -> List[PromptVersion]:
        self.get_prompt(prompt_id)
        return self.repo.list_prompt_versions(prompt_id)

    def render_prompt(
        self,
        prompt_version: PromptVersion,
        variables: Dict[str, Any],
    ) -> Tuple[str, str]:
        """
        Renders prompt template with variables and secret redaction.
        Returns (rendered_prompt, sha256_hash).
        """
        # Validate required variables declared in variables_schema
        required_vars = prompt_version.variables_schema.get("required", [])
        missing = [v for v in required_vars if v not in variables]
        if missing:
            raise InvalidPromptTemplateError(f"Missing required prompt variables: {missing}")

        rendered = prompt_version.template

        # Support both {{var}} and {var} substitution
        for key, val in variables.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", str(val))
            rendered = rendered.replace(f"{{{key}}}", str(val))

        # Redact secrets
        rendered = redact_secrets(rendered)

        # Compute SHA-256 hash
        prompt_hash = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        return rendered, prompt_hash

    def update_version_status(
        self,
        prompt_id: str,
        version: int,
        new_status: PromptStatus,
    ) -> PromptVersion:
        pv = self.get_prompt_version(prompt_id, version)
        pv.status = new_status
        return self.repo.save_prompt_version(pv)
