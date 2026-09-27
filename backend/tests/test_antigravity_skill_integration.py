"""
Unit and integration tests for Slice 7.4 — Antigravity Engineering Lab Skill & Agent Workflow Integration.
Verifies skill structure, YAML frontmatter, references, MCP configuration, and helper scripts.
"""

import os
import json
import yaml
import subprocess
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = PROJECT_ROOT / ".agents" / "skills" / "engineering-lab"
MCP_CONFIG_PATH = PROJECT_ROOT / ".agents" / "mcp_config.json"


def test_mcp_config_validity():
    """Verify that .agents/mcp_config.json exists and configures the Engineering Lab server."""
    assert MCP_CONFIG_PATH.exists(), f"Missing {MCP_CONFIG_PATH}"
    with open(MCP_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    assert "mcpServers" in config, "mcpServers key missing from mcp_config.json"
    servers = config["mcpServers"]
    assert "engineering-lab" in servers, "engineering-lab server missing from mcpServers"

    lab_server = servers["engineering-lab"]
    assert lab_server.get("command") == "python"
    args = lab_server.get("args", [])
    assert any("run_mcp_server.py" in arg for arg in args), f"run_mcp_server.py not found in args: {args}"
    assert "--transport" in args
    assert "stdio" in args


def test_skill_directory_structure_and_frontmatter():
    """Verify SKILL.md exists with valid YAML frontmatter and required fields."""
    skill_md = SKILL_DIR / "SKILL.md"
    assert skill_md.exists(), f"Missing {skill_md}"

    content = skill_md.read_text(encoding="utf-8")
    assert content.startswith("---"), "SKILL.md must start with YAML frontmatter"

    parts = content.split("---", 2)
    assert len(parts) >= 3, "Invalid frontmatter structure in SKILL.md"
    frontmatter_raw = parts[1]
    frontmatter = yaml.safe_load(frontmatter_raw)

    assert frontmatter.get("name") == "engineering-lab"
    assert "description" in frontmatter
    assert len(frontmatter["description"]) > 30


def test_skill_reference_files_exist():
    """Verify that all four required reference documents exist and have non-empty content."""
    references_dir = SKILL_DIR / "references"
    assert references_dir.is_dir()

    expected_refs = [
        "workflow.md",
        "tool-usage.md",
        "evidence-policy.md",
        "engineering-trace.md",
    ]

    for ref in expected_refs:
        ref_path = references_dir / ref
        assert ref_path.exists(), f"Missing reference file: {ref}"
        assert len(ref_path.read_text(encoding="utf-8").strip()) > 100, f"Empty reference file: {ref}"


def test_skill_content_mandates():
    """Verify that SKILL.md covers all core architectural mandates."""
    content = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

    # Workflow and Done definition
    assert "The 12-Step Engineering Lab Workflow" in content
    assert "Definition of \"Done\"" in content
    assert "IMPLEMENTED" in content and "LAB_VERIFIED" in content and "COMPLETE" in content

    # Epistemic abstention rule
    assert "Mandatory Epistemic Abstention Rule" in content
    assert "RELIABILITY_ABSTAINED" in content or "ABSTAINED" in content

    # Canonical 10 tools
    canonical_tools = [
        "inspect_application",
        "start_test_session",
        "get_application_health",
        "get_prediction",
        "get_uncertainty",
        "list_failures",
        "get_failure",
        "diagnose_failure",
        "get_evidence",
        "get_reliability_summary",
    ]
    for tool in canonical_tools:
        assert tool in content, f"Tool {tool} not documented in SKILL.md"

    # Security boundary
    assert "Security Boundary" in content


def test_references_content_depth():
    """Verify that reference documents contain expected operational guidelines."""
    tool_usage = (SKILL_DIR / "references" / "tool-usage.md").read_text(encoding="utf-8")
    assert "diagnose_failure" in tool_usage
    assert "Tool Selection Policy" in tool_usage

    evidence_policy = (SKILL_DIR / "references" / "evidence-policy.md").read_text(encoding="utf-8")
    assert "OBSERVED EVIDENCE" in evidence_policy
    assert "INFERRED FACT" in evidence_policy
    assert "HYPOTHESIS" in evidence_policy
    assert "Redaction & Credential Protection" in evidence_policy

    eng_trace = (SKILL_DIR / "references" / "engineering-trace.md").read_text(encoding="utf-8")
    assert "ENGINEERING VERIFICATION TRACE" in eng_trace
    assert "OBSERVATION" in eng_trace
    assert "EVIDENCE" in eng_trace
    assert "ACTION TAKEN" in eng_trace
    assert "INDEPENDENT VERIFICATION" in eng_trace


def test_helper_scripts_exist_and_runnable():
    """Verify that check_lab_health.py and verify_application.py exist."""
    scripts_dir = SKILL_DIR / "scripts"
    assert scripts_dir.is_dir()

    check_health = scripts_dir / "check_lab_health.py"
    verify_app = scripts_dir / "verify_application.py"

    assert check_health.exists()
    assert verify_app.exists()


def test_helper_check_lab_health_execution():
    """Run check_lab_health.py and verify exit code 0."""
    script_path = SKILL_DIR / "scripts" / "check_lab_health.py"
    proc = subprocess.run(
        ["python", str(script_path)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"check_lab_health.py failed with code {proc.returncode}:\nStdout: {proc.stdout}\nStderr: {proc.stderr}"
    assert "ALL CHECKS PASSED" in proc.stdout
    assert "Discovered 10 Canonical Tools" in proc.stdout


def test_helper_verify_application_execution():
    """Run verify_application.py and verify exit code 0 and trace format."""
    script_path = SKILL_DIR / "scripts" / "verify_application.py"
    proc = subprocess.run(
        ["python", str(script_path), "--app", "app_inventory"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"verify_application.py failed with code {proc.returncode}:\nStdout: {proc.stdout}\nStderr: {proc.stderr}"
    assert "ENGINEERING VERIFICATION TRACE" in proc.stdout
    assert "TASK:" in proc.stdout
    assert "1. OBSERVATION" in proc.stdout
    assert "2. EVIDENCE" in proc.stdout
    assert "3. INTERPRETATION & DECISION" in proc.stdout
    assert "4. INDEPENDENT VERIFICATION" in proc.stdout
    assert "Final Verdict:  VERIFIED" in proc.stdout
