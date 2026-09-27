import re
import ast
import json
import sqlite3
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone

from backend.app.prompt_lab.models import (
    EvaluationStrategy,
    EvaluationStatus,
    GroundingStatus,
    EvaluatorResult,
    GroundingClaimResult,
    EvaluationCase,
    AIExecutionRecord,
)


class JSONSchemaEvaluator:
    """Validates output against declared JSON schema."""

    def evaluate(self, raw_output: str, output_schema: Optional[Dict[str, Any]]) -> EvaluatorResult:
        if not output_schema:
            return EvaluatorResult(
                evaluator_name="JSONSchemaEvaluator",
                strategy=EvaluationStrategy.JSON_SCHEMA,
                status=EvaluationStatus.NOT_APPLICABLE,
                rationale="No output_schema declared for evaluation case or prompt version.",
            )

        # Attempt to parse json from raw_output
        cleaned = raw_output.strip()
        # Handle markdown fences if present
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
        except Exception as e:
            return EvaluatorResult(
                evaluator_name="JSONSchemaEvaluator",
                strategy=EvaluationStrategy.JSON_SCHEMA,
                status=EvaluationStatus.FAIL,
                score=0.0,
                confidence=1.0,
                rationale=f"Output is not valid JSON: {str(e)}",
                evidence=[{"raw_output_snippet": raw_output[:300]}],
            )

        # Check required fields
        required = output_schema.get("required", [])
        missing = [req for req in required if req not in parsed]
        if missing:
            return EvaluatorResult(
                evaluator_name="JSONSchemaEvaluator",
                strategy=EvaluationStrategy.JSON_SCHEMA,
                status=EvaluationStatus.FAIL,
                score=0.0,
                confidence=1.0,
                rationale=f"Missing required schema fields: {missing}",
                evidence=[{"missing_fields": missing, "parsed_keys": list(parsed.keys())}],
            )

        # Basic type checking if declared
        properties = output_schema.get("properties", {})
        type_mismatches = []
        for key, prop_schema in properties.items():
            if key in parsed:
                expected_type = prop_schema.get("type")
                val = parsed[key]
                if expected_type == "string" and not isinstance(val, str):
                    type_mismatches.append(f"{key}: expected string, got {type(val).__name__}")
                elif expected_type == "integer" and not isinstance(val, int):
                    type_mismatches.append(f"{key}: expected integer, got {type(val).__name__}")
                elif expected_type == "number" and not isinstance(val, (int, float)):
                    type_mismatches.append(f"{key}: expected number, got {type(val).__name__}")
                elif expected_type == "array" and not isinstance(val, list):
                    type_mismatches.append(f"{key}: expected array, got {type(val).__name__}")
                elif expected_type == "object" and not isinstance(val, dict):
                    type_mismatches.append(f"{key}: expected object, got {type(val).__name__}")
                elif expected_type == "boolean" and not isinstance(val, bool):
                    type_mismatches.append(f"{key}: expected boolean, got {type(val).__name__}")

        if type_mismatches:
            return EvaluatorResult(
                evaluator_name="JSONSchemaEvaluator",
                strategy=EvaluationStrategy.JSON_SCHEMA,
                status=EvaluationStatus.FAIL,
                score=0.5,
                confidence=0.95,
                rationale=f"Schema type violations: {', '.join(type_mismatches)}",
                evidence=[{"type_mismatches": type_mismatches}],
            )

        return EvaluatorResult(
            evaluator_name="JSONSchemaEvaluator",
            strategy=EvaluationStrategy.JSON_SCHEMA,
            status=EvaluationStatus.PASS,
            score=1.0,
            confidence=1.0,
            rationale="Output conforms to declared JSON schema.",
            evidence=[{"keys_validated": list(parsed.keys())}],
        )


class RuleBasedEvaluator:
    """Evaluates explicit constraint rules."""

    def evaluate(self, raw_output: str, constraints: List[str]) -> EvaluatorResult:
        if not constraints:
            return EvaluatorResult(
                evaluator_name="RuleBasedEvaluator",
                strategy=EvaluationStrategy.RULE_BASED,
                status=EvaluationStatus.NOT_APPLICABLE,
                rationale="No explicit constraint rules specified.",
            )

        violations = []
        parsed_json = None
        try:
            cleaned = raw_output.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            parsed_json = json.loads(cleaned.strip())
        except Exception:
            parsed_json = None

        for c in constraints:
            c_lower = c.lower()
            if c_lower.startswith("forbidden:"):
                forbidden_items = [x.strip() for x in c.split(":", 1)[1].split(",")]
                for item in forbidden_items:
                    if item.lower() in raw_output.lower():
                        violations.append(f"Forbidden phrase found: '{item}'")
            elif c_lower.startswith("required_phrase:"):
                req = c.split(":", 1)[1].strip()
                if req.lower() not in raw_output.lower():
                    violations.append(f"Required phrase missing: '{req}'")
            elif c_lower.startswith("max_chars:"):
                try:
                    limit = int(c.split(":", 1)[1].strip())
                    if len(raw_output) > limit:
                        violations.append(f"Output length {len(raw_output)} exceeds max_chars {limit}")
                except ValueError:
                    pass
            elif c_lower.startswith("min_chars:"):
                try:
                    limit = int(c.split(":", 1)[1].strip())
                    if len(raw_output) < limit:
                        violations.append(f"Output length {len(raw_output)} is less than min_chars {limit}")
                except ValueError:
                    pass
            elif c_lower.startswith("must_contain_field:") and parsed_json:
                field = c.split(":", 1)[1].strip()
                if field not in parsed_json:
                    violations.append(f"Required JSON field missing: '{field}'")
            elif c_lower == "citation_required":
                # Check for bracketed citations like [1] or (Source: ...)
                if not re.search(r"\[\d+\]|\[source:\s*[^\]]+\]|\(source:\s*[^\)]+\)", raw_output, re.IGNORECASE):
                    violations.append("Citation required but no citation markers found in output.")

        if violations:
            return EvaluatorResult(
                evaluator_name="RuleBasedEvaluator",
                strategy=EvaluationStrategy.RULE_BASED,
                status=EvaluationStatus.FAIL,
                score=0.0,
                confidence=1.0,
                rationale=f"Violated rules: {'; '.join(violations)}",
                evidence=[{"violations": violations}],
            )

        return EvaluatorResult(
            evaluator_name="RuleBasedEvaluator",
            strategy=EvaluationStrategy.RULE_BASED,
            status=EvaluationStatus.PASS,
            score=1.0,
            confidence=1.0,
            rationale="All rule constraints satisfied.",
            evidence=[{"constraints_checked": constraints}],
        )


class ExactMatchEvaluator:
    """Evaluates strict exact output match."""

    def evaluate(self, raw_output: str, expected_output: Optional[Any]) -> EvaluatorResult:
        if expected_output is None:
            return EvaluatorResult(
                evaluator_name="ExactMatchEvaluator",
                strategy=EvaluationStrategy.EXACT_MATCH,
                status=EvaluationStatus.NOT_APPLICABLE,
                rationale="No expected_output specified for exact matching.",
            )

        actual_str = str(raw_output).strip()
        expected_str = str(expected_output).strip()

        # Direct string equality or JSON canonical equality
        match = (actual_str == expected_str)
        if not match:
            try:
                actual_obj = json.loads(actual_str)
                expected_obj = json.loads(expected_str) if isinstance(expected_output, str) else expected_output
                match = (actual_obj == expected_obj)
            except Exception:
                match = False

        if match:
            return EvaluatorResult(
                evaluator_name="ExactMatchEvaluator",
                strategy=EvaluationStrategy.EXACT_MATCH,
                status=EvaluationStatus.PASS,
                score=1.0,
                confidence=1.0,
                rationale="Output matches expected output exactly.",
            )
        else:
            return EvaluatorResult(
                evaluator_name="ExactMatchEvaluator",
                strategy=EvaluationStrategy.EXACT_MATCH,
                status=EvaluationStatus.FAIL,
                score=0.0,
                confidence=1.0,
                rationale="Output does not match expected output.",
                evidence=[{
                    "actual_snippet": actual_str[:200],
                    "expected_snippet": expected_str[:200],
                }],
            )


class CodeExecutionEvaluator:
    """Controlled safe evaluation boundary for generated code."""

    FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__", "open", "system", "spawn"}

    def evaluate(self, raw_output: str, expected_behavior: str) -> EvaluatorResult:
        # Extract code from markdown fences if any
        code = raw_output.strip()
        if "```python" in code:
            code = code.split("```python", 1)[1].split("```", 1)[0].strip()
        elif "```" in code:
            code = code.split("```", 1)[1].split("```", 1)[0].strip()

        # AST syntax & safety validation
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return EvaluatorResult(
                evaluator_name="CodeExecutionEvaluator",
                strategy=EvaluationStrategy.CODE_EXECUTION,
                status=EvaluationStatus.FAIL,
                score=0.0,
                confidence=1.0,
                rationale=f"Python syntax error in generated code: {str(e)}",
                evidence=[{"syntax_error": str(e), "line": getattr(e, 'lineno', 0)}],
            )

        # Inspect AST for safety violations
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in {"os", "sys", "subprocess", "shutil", "socket", "http"}:
                        return EvaluatorResult(
                            evaluator_name="CodeExecutionEvaluator",
                            strategy=EvaluationStrategy.CODE_EXECUTION,
                            status=EvaluationStatus.FAIL,
                            score=0.0,
                            confidence=1.0,
                            rationale=f"Security violation: forbidden import '{alias.name}' in evaluated code.",
                            evidence=[{"forbidden_import": alias.name}],
                        )
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in self.FORBIDDEN_CALLS:
                    return EvaluatorResult(
                        evaluator_name="CodeExecutionEvaluator",
                        strategy=EvaluationStrategy.CODE_EXECUTION,
                        status=EvaluationStatus.FAIL,
                        score=0.0,
                        confidence=1.0,
                        rationale=f"Security violation: forbidden call '{node.func.id}' in evaluated code.",
                        evidence=[{"forbidden_call": node.func.id}],
                    )

        # Safe restricted execution
        safe_globals = {
            "__builtins__": {
                "range": range,
                "len": len,
                "int": int,
                "str": str,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "set": set,
                "sum": sum,
                "min": min,
                "max": max,
                "round": round,
            }
        }
        local_scope: Dict[str, Any] = {}
        try:
            exec(code, safe_globals, local_scope)
        except Exception as e:
            return EvaluatorResult(
                evaluator_name="CodeExecutionEvaluator",
                strategy=EvaluationStrategy.CODE_EXECUTION,
                status=EvaluationStatus.FAIL,
                score=0.0,
                confidence=0.9,
                rationale=f"Runtime error during restricted execution: {type(e).__name__}: {str(e)}",
                evidence=[{"runtime_error": str(e)}],
            )

        return EvaluatorResult(
            evaluator_name="CodeExecutionEvaluator",
            strategy=EvaluationStrategy.CODE_EXECUTION,
            status=EvaluationStatus.PASS,
            score=1.0,
            confidence=1.0,
            rationale="Code successfully parsed and executed within restricted boundary.",
            evidence=[{"defined_symbols": list(local_scope.keys())}],
        )


class SQLExecutionEvaluator:
    """Controlled safe evaluation boundary for generated SQL queries."""

    FORBIDDEN_KEYWORDS = {"drop ", "alter ", "truncate ", "grant ", "revoke "}

    def evaluate(self, raw_output: str, schema_ddl: Optional[str] = None) -> EvaluatorResult:
        query = raw_output.strip()
        if "```sql" in query:
            query = query.split("```sql", 1)[1].split("```", 1)[0].strip()
        elif "```" in query:
            query = query.split("```", 1)[1].split("```", 1)[0].strip()

        query_lower = query.lower()
        for kw in self.FORBIDDEN_KEYWORDS:
            if kw in query_lower:
                return EvaluatorResult(
                    evaluator_name="SQLExecutionEvaluator",
                    strategy=EvaluationStrategy.SQL_EXECUTION,
                    status=EvaluationStatus.FAIL,
                    score=0.0,
                    confidence=1.0,
                    rationale=f"Security violation: forbidden SQL keyword '{kw.strip()}' detected.",
                    evidence=[{"forbidden_sql": kw.strip()}],
                )

        # Validate with in-memory SQLite sandbox
        try:
            conn = sqlite3.connect(":memory:")
            cursor = conn.cursor()
            if schema_ddl:
                cursor.executescript(schema_ddl)
            # Explain query plan to test validity without requiring massive data
            cursor.execute(f"EXPLAIN QUERY PLAN {query}")
            conn.close()
        except Exception as e:
            return EvaluatorResult(
                evaluator_name="SQLExecutionEvaluator",
                strategy=EvaluationStrategy.SQL_EXECUTION,
                status=EvaluationStatus.FAIL,
                score=0.0,
                confidence=0.9,
                rationale=f"SQL compilation or syntax error: {str(e)}",
                evidence=[{"sql_error": str(e), "query": query[:200]}],
            )

        return EvaluatorResult(
            evaluator_name="SQLExecutionEvaluator",
            strategy=EvaluationStrategy.SQL_EXECUTION,
            status=EvaluationStatus.PASS,
            score=1.0,
            confidence=1.0,
            rationale="SQL query is syntactically valid and executed in sandbox successfully.",
            evidence=[{"validated_query_length": len(query)}],
        )


class GroundingEvaluator:
    """Evaluates whether material claims in output are supported by retrieved sources."""

    def evaluate(self, raw_output: str, sources: List[Dict[str, Any]]) -> EvaluatorResult:
        if not sources:
            return EvaluatorResult(
                evaluator_name="GroundingEvaluator",
                strategy=EvaluationStrategy.GROUNDING,
                status=EvaluationStatus.UNKNOWN,
                score=0.5,
                confidence=0.5,
                rationale="No source evidence provided to evaluate grounding.",
                metadata={"grounding_status": GroundingStatus.UNKNOWN.value},
            )

        # Pool text from sources
        combined_source_text = " ".join([
            str(s.get("content", s.get("text", ""))) for s in sources
        ]).lower()

        # Extract sentences/claims from output (or JSON string values)
        sentences = []
        try:
            cleaned = raw_output.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            parsed = json.loads(cleaned.strip())
            if isinstance(parsed, dict):
                for val in parsed.values():
                    if isinstance(val, str):
                        for s in re.split(r"[.!?\n]", val):
                            s_clean = re.sub(r"\[source:\s*[^\]]+\]", "", s, flags=re.IGNORECASE).strip()
                            if len(s_clean) > 15 and len(s_clean.split()) >= 3:
                                sentences.append(s_clean)
        except Exception:
            pass

        if not sentences:
            for s in re.split(r"[.!?\n]", raw_output):
                s_clean = re.sub(r"\[source:\s*[^\]]+\]", "", s, flags=re.IGNORECASE).strip()
                if len(s_clean) > 15 and len(s_clean.split()) >= 3:
                    sentences.append(s_clean)
        if not sentences:
            return EvaluatorResult(
                evaluator_name="GroundingEvaluator",
                strategy=EvaluationStrategy.GROUNDING,
                status=EvaluationStatus.PASS,
                score=1.0,
                confidence=0.8,
                rationale="Output contains no substantial factual claims.",
                metadata={"grounding_status": GroundingStatus.SUPPORTED.value},
            )

        claims: List[GroundingClaimResult] = []
        supported_count = 0
        unsupported_count = 0

        for sentence in sentences:
            sentence_clean = sentence.lower()
            # Extract key tokens (length > 4)
            tokens = [w for w in re.findall(r"\b[a-zA-Z0-9_\-]{4,}\b", sentence_clean)]
            if not tokens:
                continue

            matches = sum(1 for t in tokens if t in combined_source_text)
            overlap_ratio = matches / len(tokens) if tokens else 0.0

            if overlap_ratio >= 0.5:
                claims.append(GroundingClaimResult(
                    claim_text=sentence,
                    status=GroundingStatus.SUPPORTED,
                    supporting_source_ids=[s.get("source_id", "src") for s in sources if any(t in str(s).lower() for t in tokens)],
                    rationale=f"Token overlap {overlap_ratio:.2f} with source context.",
                ))
                supported_count += 1
            else:
                claims.append(GroundingClaimResult(
                    claim_text=sentence,
                    status=GroundingStatus.UNSUPPORTED,
                    rationale=f"Insufficient source overlap ({overlap_ratio:.2f}) for claim.",
                ))
                unsupported_count += 1

        total_claims = supported_count + unsupported_count
        score = supported_count / total_claims if total_claims > 0 else 1.0

        if unsupported_count == 0:
            status = EvaluationStatus.PASS
            grounding_status = GroundingStatus.SUPPORTED
            rationale = f"All {total_claims} material claims grounded in source evidence."
        elif supported_count > 0:
            status = EvaluationStatus.PARTIAL
            grounding_status = GroundingStatus.PARTIALLY_SUPPORTED
            rationale = f"{unsupported_count} of {total_claims} claims lack sufficient grounding in source evidence."
        else:
            status = EvaluationStatus.FAIL
            grounding_status = GroundingStatus.UNSUPPORTED
            rationale = "Material claims are unsupported by retrieved sources."

        return EvaluatorResult(
            evaluator_name="GroundingEvaluator",
            strategy=EvaluationStrategy.GROUNDING,
            status=status,
            score=round(score, 4),
            confidence=0.9,
            rationale=rationale,
            claims=claims,
            metadata={"grounding_status": grounding_status.value},
        )


class SemanticJudgeEvaluator:
    """Semantic correctness evaluator with explicit provenance."""

    def __init__(self, judge_model: str = "judge-deterministic-v1", judge_version: str = "1.0"):
        self.judge_model = judge_model
        self.judge_version = judge_version

    def evaluate(
        self,
        raw_output: str,
        expected_behavior: str,
        expected_output: Optional[Any] = None,
        constraints: Optional[List[str]] = None,
    ) -> EvaluatorResult:
        actual_lower = raw_output.lower().strip()
        expected_behavior_lower = expected_behavior.lower().strip()

        # Semantic relevance heuristic over expected behavior keywords
        behavior_keywords = [
            w for w in re.findall(r"\b[a-zA-Z]{4,}\b", expected_behavior_lower)
            if w not in {"must", "should", "ensure", "output", "return", "provide", "contain", "valid", "json", "with", "that", "this", "from", "have", "based", "only"}
        ]

        if not behavior_keywords:
            matched_ratio = 1.0
        else:
            matched = sum(1 for kw in behavior_keywords if kw in actual_lower)
            matched_ratio = matched / len(behavior_keywords)

        # Check refusal / error indicators
        has_error = any(phrase in actual_lower for phrase in [
            "internal error", "cannot fulfill", "exception occurred", "unhandled error"
        ])

        if has_error:
            score = 0.1
            status = EvaluationStatus.FAIL
            rationale = "Output indicates an unhandled error or execution refusal."
        elif matched_ratio >= 0.5:
            score = round(matched_ratio, 3)
            status = EvaluationStatus.PASS
            rationale = f"Semantic criteria met ({matched_ratio:.1%} keyword alignment with expected behavior)."
        elif matched_ratio >= 0.3:
            score = round(matched_ratio, 3)
            status = EvaluationStatus.PARTIAL
            rationale = f"Partial semantic fulfillment ({matched_ratio:.1%} alignment)."
        else:
            score = round(matched_ratio, 3)
            status = EvaluationStatus.FAIL
            rationale = f"Semantic divergence from expected behavior ({matched_ratio:.1%} alignment)."

        return EvaluatorResult(
            evaluator_name="SemanticJudgeEvaluator",
            strategy=EvaluationStrategy.SEMANTIC_JUDGE,
            status=status,
            score=score,
            confidence=0.85,
            rationale=rationale,
            metadata={
                "judge_model": self.judge_model,
                "judge_version": self.judge_version,
                "judge_prompt_version": "1.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


class CompositeEvaluator:
    """
    Composite evaluator that executes deterministic evaluators first,
    followed by Grounding and Semantic evaluation.
    Enforces that deterministic failures cannot be overridden by LLM judges.
    """

    def __init__(self):
        self.schema_evaluator = JSONSchemaEvaluator()
        self.rule_evaluator = RuleBasedEvaluator()
        self.exact_evaluator = ExactMatchEvaluator()
        self.code_evaluator = CodeExecutionEvaluator()
        self.sql_evaluator = SQLExecutionEvaluator()
        self.grounding_evaluator = GroundingEvaluator()
        self.semantic_evaluator = SemanticJudgeEvaluator()

    def evaluate_case(
        self,
        case: EvaluationCase,
        raw_output: str,
        output_schema: Optional[Dict[str, Any]] = None,
    ) -> Tuple[EvaluationStatus, List[EvaluatorResult], Optional[float]]:
        results: List[EvaluatorResult] = []

        # 1. Deterministic Evaluation
        # Exact match if requested
        if case.evaluation_strategy == EvaluationStrategy.EXACT_MATCH or case.expected_output is not None:
            r_exact = self.exact_evaluator.evaluate(raw_output, case.expected_output)
            results.append(r_exact)

        # JSON schema
        if output_schema or case.evaluation_strategy == EvaluationStrategy.JSON_SCHEMA:
            r_schema = self.schema_evaluator.evaluate(raw_output, output_schema)
            results.append(r_schema)

        # Rules
        if case.constraints or case.evaluation_strategy == EvaluationStrategy.RULE_BASED:
            r_rule = self.rule_evaluator.evaluate(raw_output, case.constraints)
            results.append(r_rule)

        # Code execution
        if case.evaluation_strategy == EvaluationStrategy.CODE_EXECUTION:
            r_code = self.code_evaluator.evaluate(raw_output, case.expected_behavior)
            results.append(r_code)

        # SQL execution
        if case.evaluation_strategy == EvaluationStrategy.SQL_EXECUTION:
            r_sql = self.sql_evaluator.evaluate(raw_output)
            results.append(r_sql)

        # 2. Grounding Evaluation
        if case.sources or case.evaluation_strategy == EvaluationStrategy.GROUNDING:
            r_ground = self.grounding_evaluator.evaluate(raw_output, case.sources)
            results.append(r_ground)

        # 3. Semantic Evaluation
        if case.evaluation_strategy in {EvaluationStrategy.SEMANTIC_JUDGE, EvaluationStrategy.LLM_AS_JUDGE, EvaluationStrategy.COMPOSITE}:
            r_sem = self.semantic_evaluator.evaluate(
                raw_output=raw_output,
                expected_behavior=case.expected_behavior,
                expected_output=case.expected_output,
                constraints=case.constraints,
            )
            results.append(r_sem)

        # Filter out NOT_APPLICABLE for scoring
        active_results = [r for r in results if r.status != EvaluationStatus.NOT_APPLICABLE]

        if not active_results:
            return EvaluationStatus.UNKNOWN, results, 0.0

        # Check for deterministic failures first
        deterministic_strategies = {
            EvaluationStrategy.JSON_SCHEMA,
            EvaluationStrategy.RULE_BASED,
            EvaluationStrategy.EXACT_MATCH,
            EvaluationStrategy.CODE_EXECUTION,
            EvaluationStrategy.SQL_EXECUTION,
        }
        for r in active_results:
            if r.strategy in deterministic_strategies and r.status == EvaluationStatus.FAIL:
                return EvaluationStatus.FAIL, results, r.score

        # Check for epistemic ABSTAINED or UNKNOWN
        if any(r.status == EvaluationStatus.ABSTAINED for r in active_results):
            return EvaluationStatus.ABSTAINED, results, None
        if any(r.status == EvaluationStatus.UNKNOWN for r in active_results):
            return EvaluationStatus.UNKNOWN, results, None

        # Check for any remaining failures
        if any(r.status == EvaluationStatus.FAIL for r in active_results):
            return EvaluationStatus.FAIL, results, 0.0

        if any(r.status == EvaluationStatus.PARTIAL for r in active_results):
            return EvaluationStatus.PARTIAL, results, 0.5

        # All passed!
        scores = [r.score for r in active_results if r.score is not None]
        avg_score = sum(scores) / len(scores) if scores else 1.0
        return EvaluationStatus.PASS, results, avg_score
