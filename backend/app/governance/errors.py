class GovernanceError(Exception):
    """Base exception for all governance errors."""
    pass


class RecommendationNotFoundError(GovernanceError):
    pass


class ApprovalRequestNotFoundError(GovernanceError):
    pass


class ApprovalRequestImmutableError(GovernanceError):
    pass


class InvalidApprovalStateTransitionError(GovernanceError):
    pass


class HumanIdentityRequiredError(GovernanceError):
    pass


class AIAgentCannotApproveError(GovernanceError):
    pass


class ChangeAuthorizationNotFoundError(GovernanceError):
    pass


class AuthorizationExpiredError(GovernanceError):
    pass


class AuthorizationRevokedError(GovernanceError):
    pass


class EvidencePackageNotFoundError(GovernanceError):
    pass


class EvidencePackageTamperedError(GovernanceError):
    pass


class ArtifactMismatchError(GovernanceError):
    pass


class CommitMismatchError(GovernanceError):
    pass


class PolicyViolationError(GovernanceError):
    pass


class ConsequentialChangeBlockedError(GovernanceError):
    pass
