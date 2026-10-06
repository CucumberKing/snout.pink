from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from services.mcp_tokens.mcp_token_service import (
    SUBSCRIPTIONS_READ,
    SUBSCRIPTIONS_WRITE,
    InvalidMcpTokenScopesError,
    normalize_scopes,
)

McpScope = Literal["subscriptions:read", "subscriptions:write"]


class McpTokenCreateRequest(BaseModel):
    """Request to create a personal MCP token."""

    name: str = Field(min_length=1, max_length=80)
    scopes: list[McpScope] = Field(
        default_factory=lambda: [SUBSCRIPTIONS_READ, SUBSCRIPTIONS_WRITE]
    )

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped

    @field_validator("scopes")
    @classmethod
    def check_scopes(cls, value: list[str]) -> list[str]:
        try:
            return normalize_scopes(value)
        except InvalidMcpTokenScopesError as exc:
            raise ValueError(str(exc)) from exc


class McpTokenResponse(BaseModel):
    """A stored token without its secret."""

    token_id: str
    name: str
    token_prefix: str
    scopes: list[str]
    created_at_ts: float
    last_used_at_ts: float | None


class McpTokenListResponse(BaseModel):
    """Live tokens for the current user."""

    mcp_tokens: list[McpTokenResponse]
    total: int


class McpTokenCreatedResponse(McpTokenResponse):
    """Create response. `token` is shown only here."""

    token: str
    mcp_url: str
    client_config: dict[str, Any]
