"""FastMCP resource server for subscription tools.

Passkey sessions stay on the HTTP API. This server accepts personal bearer tokens.
"""

from fastmcp import FastMCP
from fastmcp.server.auth import AccessToken, TokenVerifier

from config.config import settings
from interfaces.mcp.subscriptions import register_subscription_tools
from services.mcp_tokens.mcp_token_service import SUBSCRIPTIONS_READ, verify_mcp_token


class SnoutTokenVerifier(TokenVerifier):
    """Verify snout personal access tokens."""

    def __init__(self) -> None:
        super().__init__(
            base_url=settings.resolved_public_base_url(),
            required_scopes=[SUBSCRIPTIONS_READ],
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        """Return an access token FastMCP can authorize, or None."""
        document = await verify_mcp_token(token)
        if document is None:
            return None
        return AccessToken(
            token=token,
            client_id=document.token_id,
            scopes=list(document.scopes),
            expires_at=None,
            subject=document.user_id,
        )


def build_mcp(auth: TokenVerifier | None = None) -> FastMCP:
    """Create the MCP server and register the subscription tools."""
    mcp = FastMCP("snout", auth=auth or SnoutTokenVerifier())
    register_subscription_tools(mcp)
    return mcp
