import pytest
from backend.app.control_plane.redaction import RedactionEngine


def test_redact_bearer_token():
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-ID"
    sanitized, tags = RedactionEngine.redact_text(text)
    assert "Bearer [REDACTED_TOKEN]" in sanitized
    assert "BEARER_TOKEN" in tags


def test_redact_jwt():
    text = "Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c in url"
    sanitized, tags = RedactionEngine.redact_text(text)
    assert "[REDACTED_JWT]" in sanitized
    assert "JWT_TOKEN" in tags


def test_redact_aws_keys():
    text = "aws_key = AKIAIOSFODNN7EXAMPLE and secret aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    sanitized, tags = RedactionEngine.redact_text(text)
    assert "[REDACTED_AWS_KEY]" in sanitized
    assert "[REDACTED_AWS_SECRET]" in sanitized


def test_redact_api_key():
    text = "Bearer sk-proj-1234567890abcdefghijklmnopqrstuvwxyz"
    sanitized, tags = RedactionEngine.redact_text(text)
    assert "[REDACTED_API_KEY]" in sanitized or "[REDACTED_TOKEN]" in sanitized


def test_redact_cookie_and_password():
    text = "Cookie: session_id=xyz123; user_pref=dark\npassword: 'supersecretpassword123'"
    sanitized, tags = RedactionEngine.redact_text(text)
    assert "[REDACTED_COOKIE]" in sanitized
    assert "[REDACTED_PASSWORD]" in sanitized


def test_redact_private_key():
    text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0Y...\n-----END RSA PRIVATE KEY-----"
    sanitized, tags = RedactionEngine.redact_text(text)
    assert "[REDACTED_PRIVATE_KEY]" in sanitized


def test_redact_nested_dictionary():
    data = {
        "user": "developer",
        "auth": {
            "password": "my_secret_password",
            "token": "Bearer abcdef1234567890==",
        },
        "meta": ["normal", "sk-1234567890abcdefghijk1234567890"],
    }
    sanitized, tags = RedactionEngine.redact_value(data)
    assert sanitized["auth"]["password"] == "[REDACTED_SENSITIVE_FIELD]"
    assert "[REDACTED_TOKEN]" in str(sanitized["auth"]["token"]) or "[REDACTED_SENSITIVE_FIELD]" in str(sanitized["auth"]["token"])
    assert "[REDACTED_API_KEY]" in str(sanitized["meta"])
