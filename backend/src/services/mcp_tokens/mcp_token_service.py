"""Create, list, revoke, and verify MCP personal access tokens.

The bearer a client sends is `snout_<token_id>_<secret>`. token_id selects the
row. The secret is checked with Argon2id and is never stored.
"""

import asyncio
import secrets

import arrow
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from config.config import settings
from config.logging import get_logger
from models.mcp_token import McpToken

log = get_logger(__name__)

SUBSCRIPTIONS_READ = "subscriptions:read"
SUBSCRIPTIONS_WRITE = "subscriptions:write"
ALLOWED_SCOPES = (SUBSCRIPTIONS_READ, SUBSCRIPTIONS_WRITE)

_TOKEN_PREFIX = "snout_"
_MAX_TOKEN_LENGTH = 120
_PREFIX_ID_CHARS = 8

_hasher = PasswordHasher()
_DUMMY_SECRET = secrets.token_hex(32)
_DUMMY_HASH = _hasher.hash(_DUMMY_SECRET)


class InvalidMcpTokenScopesError(Exception):
    """The requested scope set is not allowed."""


def mcp_url() -> str:
    """Public URL clients should call."""
    return f"{settings.resolved_public_base_url()}/mcp"


def client_config(token: str) -> dict[str, object]:
    """Snippet a user can paste into an MCP client."""
    return {
        "mcpServers": {
            "snout": {
                "url": mcp_url(),
                "headers": {"Authorization": f"Bearer {token}"},
            }
        }
    }


def normalize_scopes(scopes: list[str]) -> list[str]:
    """Drop duplicates and require read. Write without read is rejected."""
    unique = list(dict.fromkeys(scopes))
    unknown = [scope for scope in unique if scope not in ALLOWED_SCOPES]
    if unknown:
        raise InvalidMcpTokenScopesError(f"Unknown scopes: {', '.join(unknown)}")
    if SUBSCRIPTIONS_READ not in unique:
        raise InvalidMcpTokenScopesError("subscriptions:read is required")
    return unique


async def create_mcp_token(
    user_id: str,
    name: str,
    scopes: list[str],
) -> tuple[McpToken, str]:
    """Insert a token and return it with the one-time bearer secret."""
    stored_scopes = normalize_scopes(scopes)
    token_id = secrets.token_hex(16)
    secret = secrets.token_hex(32)
    raw = f"{_TOKEN_PREFIX}{token_id}_{secret}"
    secret_hash = await asyncio.to_thread(_hasher.hash, secret)
    document = McpToken(
        token_id=token_id,
        user_id=user_id,
        name=name,
        token_prefix=raw[: len(_TOKEN_PREFIX) + _PREFIX_ID_CHARS],
        secret_hash=secret_hash,
        scopes=stored_scopes,
    )
    await document.insert()
    log.info(
        "mcp_token_created",
        user_id=user_id,
        token_id=token_id,
        token_prefix=document.token_prefix,
        scopes=stored_scopes,
    )
    return document, raw


async def list_mcp_tokens(user_id: str) -> list[McpToken]:
    """Return live tokens for a user, newest first."""
    tokens = await McpToken.find(McpToken.user_id == user_id).to_list()
    live = [token for token in tokens if token.revoked_at_ts is None]
    live.sort(key=lambda token: token.created_at_ts, reverse=True)
    return live


async def revoke_mcp_token(user_id: str, token_id: str) -> None:
    """Mark a token revoked. Missing and foreign ids raise LookupError."""
    document = await McpToken.find_one(
        McpToken.token_id == token_id,
        McpToken.user_id == user_id,
    )
    if document is None or document.revoked_at_ts is not None:
        raise LookupError(token_id)
    document.revoked_at_ts = arrow.utcnow().timestamp()
    await document.save()
    log.info(
        "mcp_token_revoked",
        user_id=user_id,
        token_id=token_id,
        token_prefix=document.token_prefix,
    )


async def delete_mcp_tokens_for_user(user_id: str) -> None:
    """Remove every token when the account goes away."""
    await McpToken.find(McpToken.user_id == user_id).delete()
    log.info("mcp_tokens_deleted", user_id=user_id)


async def verify_mcp_token(raw: str) -> McpToken | None:
    """Return the token row when the bearer is valid and not revoked."""
    parsed = _parse(raw)
    document: McpToken | None = None
    secret = ""
    if parsed is not None:
        token_id, secret = parsed
        document = await McpToken.find_one(McpToken.token_id == token_id)

    if document is None:
        await asyncio.to_thread(_verify_dummy)
        return None

    matches = await asyncio.to_thread(_verify, document.secret_hash, secret)
    if not matches or document.revoked_at_ts is not None:
        return None

    document.last_used_at_ts = arrow.utcnow().timestamp()
    if _hasher.check_needs_rehash(document.secret_hash):
        document.secret_hash = await asyncio.to_thread(_hasher.hash, secret)
    try:
        await document.save()
    except Exception as exc:
        log.exception(
            "mcp_token_use_update_failed",
            token_id=document.token_id,
            token_prefix=document.token_prefix,
            error=str(exc),
            error_type=type(exc).__name__,
        )
    return document


def _parse(raw: str) -> tuple[str, str] | None:
    if len(raw) > _MAX_TOKEN_LENGTH or not raw.startswith(_TOKEN_PREFIX):
        return None
    token_id, separator, secret = raw[len(_TOKEN_PREFIX) :].partition("_")
    if separator != "_" or not token_id or not secret:
        return None
    if not token_id.isalnum() or not secret.isalnum():
        return None
    return token_id, secret


def _verify(secret_hash: str, secret: str) -> bool:
    try:
        _hasher.verify(secret_hash, secret)
    except (VerifyMismatchError, InvalidHashError):
        return False
    return True


def _verify_dummy() -> None:
    _verify(_DUMMY_HASH, _DUMMY_SECRET)
