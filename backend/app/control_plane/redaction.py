import re
from typing import Any
from pydantic import BaseModel


class RedactionEngine:
    """
    Security boundary redaction engine.
    Ensures no passwords, API keys, access tokens, cookies, JWTs, or private keys
    ever leave the control plane to the agent or external callers.
    """

    PATTERNS: list[tuple[str, re.Pattern, str]] = [
        # Bearer tokens
        (
            "BEARER_TOKEN",
            re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
            "Bearer [REDACTED_TOKEN]",
        ),
        # JSON Web Tokens (JWT)
        (
            "JWT_TOKEN",
            re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+\b"),
            "[REDACTED_JWT]",
        ),
        # AWS Access Key ID
        (
            "AWS_ACCESS_KEY",
            re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
            "[REDACTED_AWS_KEY]",
        ),
        # AWS Secret Access Key
        (
            "AWS_SECRET_KEY",
            re.compile(r"(?i)(aws_secret_access_key|aws_secret_key)\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{40}['\"]?"),
            r"\1=[REDACTED_AWS_SECRET]",
        ),
        # OpenAI / generic sk- API keys
        (
            "API_KEY",
            re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
            "[REDACTED_API_KEY]",
        ),
        # Passwords in query strings or JSON
        (
            "PASSWORD",
            re.compile(r"(?i)(['\"]?(?:password|passwd|pwd|secret|api_key|token)['\"]?\s*[:=]\s*['\"])([^'\"]+)(['\"])"),
            r"\1[REDACTED_PASSWORD]\3",
        ),
        # Cookie header
        (
            "COOKIE",
            re.compile(r"(?i)(Cookie\s*:\s*)([^\r\n]+)"),
            r"\1[REDACTED_COOKIE]",
        ),
        # Authorization header (for non-Bearer auth schemes like Basic, Custom)
        (
            "AUTHORIZATION_HEADER",
            re.compile(r"(?i)\bAuthorization\s*:\s*(?!Bearer\s+)(\S[^\r\n]*)"),
            "Authorization: [REDACTED_AUTH]",
        ),
        # PEM Private Keys
        (
            "PRIVATE_KEY",
            re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
            "[REDACTED_PRIVATE_KEY]",
        ),
    ]

    @classmethod
    def redact_text(cls, text: str) -> tuple[str, list[str]]:
        """
        Redacts sensitive tokens from a string.
        Returns: (sanitized_text, list_of_redaction_tags)
        """
        if not text or not isinstance(text, str):
            return text, []

        sanitized = text
        applied_tags = []

        for tag, pattern, replacement in cls.PATTERNS:
            if pattern.search(sanitized):
                sanitized = pattern.sub(replacement, sanitized)
                applied_tags.append(tag)

        return sanitized, applied_tags

    @classmethod
    def redact_value(cls, val: Any) -> tuple[Any, list[str]]:
        """
        Recursively redacts strings, dictionaries, lists, and Pydantic models.
        """
        applied: list[str] = []

        if isinstance(val, str):
            res, tags = cls.redact_text(val)
            applied.extend(tags)
            return res, list(set(applied))

        elif isinstance(val, dict):
            new_dict = {}
            for k, v in val.items():
                # Check sensitive key names directly
                if any(s in k.lower() for s in ["password", "passwd", "secret", "token", "apikey", "api_key", "cookie"]):
                    new_dict[k] = "[REDACTED_SENSITIVE_FIELD]"
                    applied.append("SENSITIVE_KEY")
                else:
                    redacted_v, tags = cls.redact_value(v)
                    new_dict[k] = redacted_v
                    applied.extend(tags)
            return new_dict, list(set(applied))

        elif isinstance(val, list):
            new_list = []
            for item in val:
                redacted_item, tags = cls.redact_value(item)
                new_list.append(redacted_item)
                applied.extend(tags)
            return new_list, list(set(applied))

        elif isinstance(val, BaseModel):
            model_dict = val.model_dump()
            redacted_dict, tags = cls.redact_value(model_dict)
            try:
                reconstructed = type(val)(**redacted_dict)
                return reconstructed, tags
            except Exception:
                return redacted_dict, tags

        return val, list(set(applied))
