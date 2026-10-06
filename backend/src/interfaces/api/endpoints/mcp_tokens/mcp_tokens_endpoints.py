from fastapi import APIRouter, Depends, HTTPException, status

from interfaces.api.dependencies import get_current_user
from interfaces.api.endpoints.mcp_tokens.mcp_tokens_schemas import (
    McpTokenCreatedResponse,
    McpTokenCreateRequest,
    McpTokenListResponse,
    McpTokenResponse,
)
from models import User
from models.mcp_token import McpToken
from services.mcp_tokens.mcp_token_service import (
    client_config,
    create_mcp_token,
    list_mcp_tokens,
    mcp_url,
    revoke_mcp_token,
)

router = APIRouter()


def _to_response(token: McpToken) -> McpTokenResponse:
    return McpTokenResponse(
        token_id=token.token_id,
        name=token.name,
        token_prefix=token.token_prefix,
        scopes=list(token.scopes),
        created_at_ts=token.created_at_ts,
        last_used_at_ts=token.last_used_at_ts,
    )


@router.get("/mcp-tokens", response_model=McpTokenListResponse)
async def list_mcp_tokens_endpoint(
    user: User = Depends(get_current_user),
) -> McpTokenListResponse:
    """List personal MCP tokens. Secrets are not included."""
    tokens = await list_mcp_tokens(user.user_id)
    return McpTokenListResponse(
        mcp_tokens=[_to_response(token) for token in tokens],
        total=len(tokens),
    )


@router.post(
    "/mcp-tokens",
    response_model=McpTokenCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_mcp_token_endpoint(
    request: McpTokenCreateRequest,
    user: User = Depends(get_current_user),
) -> McpTokenCreatedResponse:
    """Create a token. The bearer secret is returned only from this call."""
    document, raw = await create_mcp_token(user.user_id, request.name, list(request.scopes))
    body = _to_response(document)
    return McpTokenCreatedResponse(
        **body.model_dump(),
        token=raw,
        mcp_url=mcp_url(),
        client_config=client_config(raw),
    )


@router.delete("/mcp-tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_mcp_token_endpoint(
    token_id: str,
    user: User = Depends(get_current_user),
) -> None:
    """Revoke one of the current user's tokens."""
    try:
        await revoke_mcp_token(user.user_id, token_id)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP token not found",
        ) from None
