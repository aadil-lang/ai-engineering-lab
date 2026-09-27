from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.api.v1.router import api_router
from backend.app.services.target_service import TargetService
from backend.app.services.test_case_service import TestCaseService
from backend.app.repositories.sqlite_repository import SQLiteRepository

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database and seed demo entities if needed
    init_db(settings.DATABASE_PATH)
    repo = SQLiteRepository(settings.DATABASE_PATH)
    target_service = TargetService(repo)
    test_case_service = TestCaseService(repo)
    # Ensure default data is present
    target_service.list_targets()
    test_case_service.list_test_cases()
    yield
    # Shutdown

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous platform for AI Application Reliability, Continuous Telemetry, and Predictive QA.",
    lifespan=lifespan,
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Direct alias for /api/reliability/cold-start
from backend.app.api.v1.cold_start import router as cold_start_router
app.include_router(cold_start_router, prefix="/api/reliability/cold-start", tags=["Cold-Start Direct Alias"])

# Direct alias for /api/reliability/uncertainty
from backend.app.api.v1.uncertainty import router as uncertainty_router
app.include_router(uncertainty_router, prefix="/api/reliability/uncertainty", tags=["Uncertainty Direct Alias"])

# Direct alias for /api/tools
from backend.app.api.v1.tools import router as tools_router
app.include_router(tools_router, prefix="/api/tools", tags=["Tools Direct Alias"])

# Mount MCP Streamable HTTP Application
from backend.app.mcp.server import create_mcp_server, create_streamable_http_app
mcp_server, mcp_adapter = create_mcp_server()
mcp_http_app = create_streamable_http_app(mcp_server, streamable_http_path="/")
app.mount("/mcp", mcp_http_app)



@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "capabilities": {
            "test_my_app": [
                "FUNCTIONAL_QA",
                "EXPLORATORY_DOGFOODING",
                "UX_UI_REVIEW",
                "AI_LLM_EVALUATION",
                "REGRESSION_QA"
            ],
            "readiness_assessment": [
                "RELIABILITY",
                "PERFORMANCE",
                "LOAD_CAPACITY",
                "FAILURE_RECOVERY",
                "SECURITY",
                "RESOURCE_BEHAVIOR",
                "OBSERVABILITY",
                "AI_RELIABILITY",
                "MAINTAINABILITY"
            ],
            "engineering_feedback_loop": "STUBBED_CONTRACT",
            "predictive_reliability": "STUBBED_CONTRACT",
            "execution_engine": "MOCK_DETERMINISTIC_RUNNER_V1",
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
