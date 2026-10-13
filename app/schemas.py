
from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict


class ActionRequest(BaseModel):
    """A structured action proposed by the AI agent."""

    model_config = ConfigDict(extra="forbid")

    tool: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    actor: str = "ai_agent"


class PolicyCheck(BaseModel):
    """The result of one security policy check."""

    policy: str
    passed: bool
    reason: str


class GateDecision(BaseModel):
    """The security gate's decision about a proposed action."""

    action_id: str
    decision: Literal["ALLOW", "REQUIRE_APPROVAL", "BLOCK"]
    reasons: list[str] = Field(default_factory=list)
    policy_checks: list[PolicyCheck] = Field(default_factory=list)
