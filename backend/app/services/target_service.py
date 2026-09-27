from backend.app.models.target import ApplicationTarget, ApplicationTargetCreate
from backend.app.repositories.base import TargetRepositoryInterface
from backend.app.core.exceptions import NotFoundException
import uuid

class TargetService:
    def __init__(self, target_repo: TargetRepositoryInterface):
        self.target_repo = target_repo

    def register_target(self, payload: ApplicationTargetCreate) -> ApplicationTarget:
        target = ApplicationTarget(
            target_id=f"tgt_{uuid.uuid4().hex[:8]}",
            name=payload.name,
            target_type=payload.target_type,
            base_url=payload.base_url,
            environment=payload.environment,
            version=payload.version,
            description=payload.description,
            metadata=payload.metadata,
        )
        return self.target_repo.create_target(target)

    def get_target(self, target_id: str) -> ApplicationTarget:
        target = self.target_repo.get_target(target_id)
        if not target:
            raise NotFoundException(f"Application target with ID '{target_id}' not found")
        return target

    def list_targets(self) -> list[ApplicationTarget]:
        targets = self.target_repo.list_targets()
        if not targets:
            # Seed default demo target if none exist
            demo_target = ApplicationTarget(
                target_id="tgt_demo_shop",
                name="AutoShop NextGen E-Commerce",
                target_type="WEB_APPLICATION",
                base_url="https://demo-autoshop.internal",
                environment="staging",
                version="2.4.1",
                description="Modern e-commerce platform with AI recommendation engine and checkout workflows",
                metadata={"framework": "Next.js", "auth_mode": "OAuth2 / JWT", "critical_paths": ["/checkout", "/search", "/assistant"]},
            )
            self.target_repo.create_target(demo_target)
            return [demo_target]
        return targets
