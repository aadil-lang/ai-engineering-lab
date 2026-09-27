import time
import logging
from typing import Any, Callable, Type
from pydantic import BaseModel, ValidationError

from backend.app.models.tools import (
    ToolMode,
    ToolResponseEnvelope,
    ToolResponseMetadata,
    ToolError,
    ToolErrorCode,
    ToolProvenance,
)
from backend.app.control_plane.context import ToolInvocationContext
from backend.app.control_plane.errors import (
    ControlPlaneError,
    InvalidRequestError,
    InternalError,
    UnauthorizedActionError,
)
from backend.app.control_plane.redaction import RedactionEngine
from backend.app.control_plane.audit import AuditLogger

logger = logging.getLogger("ai_qa_platform.control_plane.registry")


class ToolDefinition:
    """
    Metadata, schema, and handler definition for a canonical agent tool.
    Transport-agnostic and MCP-ready.
    """

    def __init__(
        self,
        name: str,
        description: str,
        mode: ToolMode,
        request_model: Type[BaseModel],
        response_model: Type[BaseModel],
        handler: Callable[[Any, ToolInvocationContext], Any],
        version: str = "1.0",
        permission_mode: str = "open",
    ):
        self.name = name
        self.description = description
        self.mode = mode
        self.request_model = request_model
        self.response_model = response_model
        self.handler = handler
        self.version = version
        self.permission_mode = permission_mode

    def get_input_schema(self) -> dict[str, Any]:
        """Returns JSON schema for request input."""
        return self.request_model.model_json_schema()

    def get_output_schema(self) -> dict[str, Any]:
        """Returns JSON schema for response output."""
        return self.response_model.model_json_schema()

    def to_mcp_tool_schema(self) -> dict[str, Any]:
        """
        Exports tool in standard MCP-compatible JSON schema format
        WITHOUT importing or coupling to the external MCP SDK.
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "read_or_action": self.mode.value,
            "inputSchema": self.get_input_schema(),
            "outputSchema": self.get_output_schema(),
            "permission_mode": self.permission_mode,
        }


class ToolRegistry:
    """
    Central registry for canonical reliability agent tools.
    Provides capability discovery, request validation, execution, and security redaction.
    """

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register_tool(self, tool: ToolDefinition):
        """Registers a canonical tool in the registry."""
        self._tools[tool.name] = tool
        logger.info(f"Registered tool '{tool.name}' (v{tool.version}, {tool.mode.value})")

    def get_tool(self, name: str) -> ToolDefinition | None:
        """Retrieves a registered tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        """Returns all registered tool definitions."""
        return list(self._tools.values())

    def list_capabilities(self) -> list[dict[str, Any]]:
        """
        Returns capability discovery metadata suitable for agent inspection.
        Generates dynamically from registered tools.
        """
        return [
            {
                "name": t.name,
                "version": t.version,
                "mode": t.mode.value,
                "description": t.description,
            }
            for t in self._tools.values()
        ]

    def validate_request(self, tool_name: str, raw_payload: dict[str, Any]) -> BaseModel:
        """Validates raw JSON dictionary against the tool's request model."""
        tool = self.get_tool(tool_name)
        if not tool:
            raise InvalidRequestError(f"Tool '{tool_name}' is not registered in the control plane.")
        try:
            return tool.request_model(**raw_payload)
        except ValidationError as e:
            raise InvalidRequestError(
                f"Validation failed for tool '{tool_name}': {e.errors()}",
                details={"errors": e.errors()},
            )

    def invoke(
        self,
        tool_name: str,
        request_obj: BaseModel,
        context: ToolInvocationContext | None = None,
        provenance: ToolProvenance | None = None,
    ) -> ToolResponseEnvelope[Any]:
        """
        Executes a registered tool through the complete Control Plane lifecycle:
        1. Tool lookup & mode authorization check
        2. Execution timing
        3. Handler invocation
        4. Security redaction
        5. Cryptographic audit recording
        6. Response envelope wrapping
        """
        start_time = time.perf_counter()
        ctx = context or ToolInvocationContext.create_default()
        prov = provenance or ToolProvenance()

        tool = self.get_tool(tool_name)
        if not tool:
            err = ToolError(
                error_code=ToolErrorCode.INVALID_REQUEST,
                message=f"Tool '{tool_name}' is not registered.",
                recoverable=False,
            )
            meta = ToolResponseMetadata(
                tool_name=tool_name,
                request_id=ctx.request_id,
                session_id=ctx.session_id,
                provenance=prov,
            )
            return ToolResponseEnvelope(success=False, data=None, error=err, metadata=meta)

        # Action tool security check
        if tool.mode == ToolMode.ACTION and tool.permission_mode == "restricted":
            if not ctx.auth_token:
                unauth_err = UnauthorizedActionError(tool.name).to_tool_error()
                meta = ToolResponseMetadata(
                    tool_name=tool.name,
                    tool_version=tool.version,
                    request_id=ctx.request_id,
                    session_id=ctx.session_id,
                    provenance=prov,
                )
                return ToolResponseEnvelope(success=False, data=None, error=unauth_err, metadata=meta)

        try:
            raw_response = tool.handler(request_obj, ctx)

            # Security redaction
            sanitized_response, _ = RedactionEngine.redact_value(raw_response)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            # Derive application_id if present
            app_id = getattr(request_obj, "application_id", None) or getattr(sanitized_response, "application_id", None)

            # Cryptographic audit recording
            AuditLogger.record_invocation(
                request_id=ctx.request_id,
                tool_name=tool.name,
                tool_version=tool.version,
                application_id=app_id,
                session_id=ctx.session_id,
                actor=ctx.actor,
                request_data=request_obj.model_dump(),
                response_data=sanitized_response.model_dump() if hasattr(sanitized_response, "model_dump") else sanitized_response,
                result_status="SUCCESS",
                execution_time_ms=elapsed_ms,
            )

            meta = ToolResponseMetadata(
                tool_name=tool.name,
                tool_version=tool.version,
                request_id=ctx.request_id,
                session_id=ctx.session_id,
                application_id=app_id,
                provenance=prov,
                execution_time_ms=round(elapsed_ms, 2),
            )

            return ToolResponseEnvelope(success=True, data=sanitized_response, error=None, metadata=meta)

        except ControlPlaneError as cpe:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            tool_err = cpe.to_tool_error()
            app_id = getattr(request_obj, "application_id", None)

            AuditLogger.record_invocation(
                request_id=ctx.request_id,
                tool_name=tool.name,
                tool_version=tool.version,
                application_id=app_id,
                session_id=ctx.session_id,
                actor=ctx.actor,
                request_data=request_obj.model_dump(),
                response_data=tool_err.model_dump(),
                result_status="ERROR",
                execution_time_ms=elapsed_ms,
                error_code=tool_err.error_code.value,
            )

            meta = ToolResponseMetadata(
                tool_name=tool.name,
                tool_version=tool.version,
                request_id=ctx.request_id,
                session_id=ctx.session_id,
                application_id=app_id,
                provenance=prov,
                execution_time_ms=round(elapsed_ms, 2),
            )
            return ToolResponseEnvelope(success=False, data=None, error=tool_err, metadata=meta)

        except Exception as ex:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(f"Unexpected error in tool '{tool.name}': {ex}", exc_info=True)
            tool_err = InternalError(f"Unexpected internal failure in '{tool.name}': {str(ex)}").to_tool_error()
            app_id = getattr(request_obj, "application_id", None)

            AuditLogger.record_invocation(
                request_id=ctx.request_id,
                tool_name=tool.name,
                tool_version=tool.version,
                application_id=app_id,
                session_id=ctx.session_id,
                actor=ctx.actor,
                request_data=request_obj.model_dump(),
                response_data=tool_err.model_dump(),
                result_status="ERROR",
                execution_time_ms=elapsed_ms,
                error_code=tool_err.error_code.value,
            )

            meta = ToolResponseMetadata(
                tool_name=tool.name,
                tool_version=tool.version,
                request_id=ctx.request_id,
                session_id=ctx.session_id,
                application_id=app_id,
                provenance=prov,
                execution_time_ms=round(elapsed_ms, 2),
            )
            return ToolResponseEnvelope(success=False, data=None, error=tool_err, metadata=meta)
