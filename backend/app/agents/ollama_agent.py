import json
import logging
import httpx
from typing import Any, Literal
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger("ai_qa_platform.ollama_agent")

AgentActionType = Literal[
    "navigate",
    "click",
    "input",
    "hover",
    "press_key",
    "scroll",
    "assert_text",
    "assert_element",
    "finish_pass",
    "finish_fail"
]

class AgentDecision(BaseModel):
    thought: str = Field(..., description="Explanation of why this action is chosen and what we expect.")
    action: AgentActionType = Field(..., description="The typed action to execute.")
    element_index: int | None = Field(None, description="The integer index [N] from the interactive elements list.")
    selector: str | None = Field(None, description="CSS or XPath selector if not using element_index.")
    value: str | None = Field(None, description="Text string to type, key to press, or text to assert.")
    url: str | None = Field(None, description="URL for navigate action.")
    direction: Literal["up", "down"] | None = Field("down", description="Direction for scroll action.")
    distance: int | None = Field(300, description="Pixel distance for scroll action.")
    reason: str | None = Field(None, description="Final explanation when calling finish_pass or finish_fail.")


SYSTEM_PROMPT = """You are an expert autonomous QA testing agent controlling a web browser to test applications.
Your job is to observe the current web page, reason about the next step toward achieving the test goal, and output exactly ONE action formatted as valid JSON.

You MUST NOT write raw code or scripts. You can only emit structured JSON decisions adhering strictly to the schema below.

### AVAILABLE ACTIONS:
1. `navigate`: Go to a new URL. Example: {"thought": "Opening home page", "action": "navigate", "url": "http://localhost:3000"}
2. `click`: Click an element by index or selector. Example: {"thought": "Clicking login button", "action": "click", "element_index": 2}
3. `input`: Type text into an input or textarea. Example: {"thought": "Entering search query", "action": "input", "element_index": 1, "value": "test user"}
4. `hover`: Hover mouse over element. Example: {"thought": "Hovering over dropdown menu", "action": "hover", "element_index": 3}
5. `press_key`: Press a keyboard key (e.g. "Enter", "Tab", "Escape"). Example: {"thought": "Submitting search by pressing Enter", "action": "press_key", "value": "Enter"}
6. `scroll`: Scroll the page up or down. Example: {"thought": "Scrolling down to see footer", "action": "scroll", "direction": "down", "distance": 400}
7. `assert_text`: Verify that specific text is visible on the page. Example: {"thought": "Verifying success message appears", "action": "assert_text", "value": "Run Started Successfully"}
8. `assert_element`: Verify that an element exists and is visible. Example: {"thought": "Checking modal dialog opened", "action": "assert_element", "element_index": 4}
9. `finish_pass`: The goal has been successfully accomplished or exploration completed with no critical bugs. Example: {"thought": "All assertions verified and goal met", "action": "finish_pass", "reason": "Workflow completed successfully"}
10. `finish_fail`: A critical bug, broken page, or assertion failure was encountered and cannot be recovered. Example: {"thought": "Form submission failed with server error 500", "action": "finish_fail", "reason": "500 Internal Server Error displayed on page"}

### RULES:
- Always prefer `element_index` referencing the numbered interactive elements list (e.g., [1], [2]).
- Keep `thought` concise (1-2 sentences).
- If you have completed the goal, ALWAYS call `finish_pass`.
- If an unrecoverable bug or missing element prevents finishing, call `finish_fail`.
- Output ONLY a single JSON object. No Markdown code fences, no extra preamble.
"""

class OllamaReasoner:
    """Reasoning engine powered by local Ollama LLM (qwen2.5-coder:7b-instruct)."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5-coder:7b-instruct",
        timeout_seconds: float = 60.0
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def is_available(self) -> bool:
        """Check if Ollama server is reachable and responsive."""
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    def decide_next_action(
        self,
        goal: str,
        test_mode: str,
        current_dom_summary: str,
        history_summary: str,
        step_number: int,
        max_steps: int,
        last_error: str | None = None
    ) -> AgentDecision:
        """Query Ollama with the current observation and history to generate the next action."""
        
        user_prompt_lines = [
            f"=== TEST MODE: {test_mode} ===",
            f"=== GOAL: {goal} ===",
            f"=== STEP: {step_number} of {max_steps} ===",
        ]
        
        if history_summary:
            user_prompt_lines.append("\n=== ACTION HISTORY ===")
            user_prompt_lines.append(history_summary)

        if last_error:
            user_prompt_lines.append(f"\n⚠️ PREVIOUS ACTION ERROR: {last_error}")
            user_prompt_lines.append("Please choose an alternative action or recover from this error.")

        user_prompt_lines.append("\n=== CURRENT PAGE OBSERVATION ===")
        user_prompt_lines.append(current_dom_summary)
        
        user_prompt_lines.append("\nRespond with the next JSON action now:")

        prompt = "\n".join(user_prompt_lines)

        payload = {
            "model": self.model,
            "system": SYSTEM_PROMPT,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 250
            }
        }

        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout_seconds
            )
            response.raise_for_status()
            res_data = response.json()
            raw_text = res_data.get("response", "").strip()
            
            # Parse JSON
            parsed = json.loads(raw_text)
            
            # Normalize action name (case-insensitive or aliases)
            if "action" in parsed and isinstance(parsed["action"], str):
                act_str = parsed["action"].lower().strip()
                if act_str in ("fill", "type"):
                    parsed["action"] = "input"
                elif act_str in ("goto", "open"):
                    parsed["action"] = "navigate"
                elif act_str in ("pass", "finish", "done", "complete"):
                    parsed["action"] = "finish_pass"
                elif act_str in ("fail", "abort"):
                    parsed["action"] = "finish_fail"
                elif act_str in ("assert", "verify"):
                    if "value" in parsed:
                        parsed["action"] = "assert_text"
                    else:
                        parsed["action"] = "assert_element"
                else:
                    parsed["action"] = act_str

            decision = AgentDecision(**parsed)
            return decision

        except json.JSONDecodeError as jde:
            logger.error(f"Failed to parse LLM JSON response: {jde}. Raw text: {raw_text}")
            # Fallback if text contains finish signals
            if "finish" in raw_text.lower() or "completed" in raw_text.lower():
                return AgentDecision(
                    thought="Goal completed according to agent output.",
                    action="finish_pass",
                    reason="Inferred completion from response."
                )
            raise ValueError(f"LLM returned invalid JSON: {raw_text[:200]}") from jde
        except ValidationError as ve:
            logger.error(f"Decision failed Pydantic schema validation: {ve}")
            raise ValueError(f"LLM decision schema error: {ve}") from ve
        except Exception as e:
            logger.error(f"Ollama inference error: {e}")
            raise
