import arrow
from beanie import Document, Indexed
from pydantic import Field


class McpToken(Document):
    """Personal access token for the remote MCP server.

    The secret itself is never stored. secret_hash is an Argon2id PHC string.
    """

    token_id: Indexed(str, unique=True) = Field(...)  # type: ignore[valid-type]
    user_id: Indexed(str) = Field(...)  # type: ignore[valid-type]
    name: str = Field(...)
    token_prefix: str = Field(...)
    secret_hash: str = Field(...)
    scopes: list[str] = Field(...)
    created_at_ts: float = Field(default_factory=lambda: arrow.utcnow().timestamp())
    last_used_at_ts: float | None = Field(default=None)
    revoked_at_ts: float | None = Field(default=None)

    class Settings:
        name = "mcp_tokens"
        use_state_management = True
