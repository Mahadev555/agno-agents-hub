"""
Egress guard for MCP endpoints.

An MCP agent's `mcp_config.url` is user-supplied and the server connects to it.
Without a check that is server-side request forgery by design: a user could
point an agent at http://169.254.169.254/ (cloud instance metadata, often
holding credentials) or at internal services that trust the network perimeter.

Policy: resolve the hostname and refuse any address that is loopback, private,
link-local, or otherwise not globally routable. An explicit allowlist can permit
specific hosts, which is how local development keeps using localhost:3001.
"""

import ipaddress
import logging
import socket
from typing import List, Optional
from urllib.parse import urlparse

from config import get_settings

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES = ("http", "https")


class MCPEndpointBlocked(ValueError):
    """Raised when an MCP URL points somewhere it must not."""


def _resolve_addresses(hostname: str) -> List[ipaddress._BaseAddress]:
    """
    Every address a hostname resolves to.

    All of them are checked, not just the first: a hostname can legitimately
    resolve to both a public and a private address, and picking one would let
    the other through.
    """
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise MCPEndpointBlocked(f"Could not resolve MCP host '{hostname}': {exc}") from exc

    addresses = []
    for info in infos:
        raw = info[4][0]
        try:
            addresses.append(ipaddress.ip_address(raw))
        except ValueError:
            continue
    if not addresses:
        raise MCPEndpointBlocked(f"MCP host '{hostname}' resolved to no usable address")
    return addresses


def _is_disallowed(address: ipaddress._BaseAddress) -> Optional[str]:
    """Why an address is refused, or None if it is acceptable."""
    if address.is_loopback:
        return "loopback"
    if address.is_link_local:
        # Covers 169.254.0.0/16, where cloud instance metadata lives.
        return "link-local"
    if address.is_private:
        return "private network"
    if address.is_reserved:
        return "reserved"
    if address.is_multicast:
        return "multicast"
    if address.is_unspecified:
        return "unspecified"
    return None


def validate_mcp_url(url: str) -> str:
    """
    Check that an MCP URL is safe to connect to.

    Returns:
        The URL, unchanged, when it is acceptable.

    Raises:
        MCPEndpointBlocked: with a reason suitable for showing the user.
    """
    settings = get_settings()

    if not url or not url.strip():
        raise MCPEndpointBlocked("MCP url must not be empty")

    parsed = urlparse(url.strip())

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise MCPEndpointBlocked(
            f"MCP url scheme '{parsed.scheme or '(none)'}' is not allowed; "
            f"use one of {list(ALLOWED_SCHEMES)}"
        )

    hostname = parsed.hostname
    if not hostname:
        raise MCPEndpointBlocked(f"MCP url '{url}' has no host")

    # An explicit allowlist entry wins, so a deployment can permit a known
    # internal MCP server (or localhost during development) on purpose.
    allowlist = settings.mcp_allowlist
    if allowlist:
        candidates = {hostname.lower()}
        if parsed.port:
            candidates.add(f"{hostname.lower()}:{parsed.port}")
        if candidates & set(allowlist):
            return url

    if settings.mcp_allow_private_network:
        logger.warning(
            f"MCP_ALLOW_PRIVATE_NETWORK is on; skipping egress checks for {hostname}"
        )
        return url

    for address in _resolve_addresses(hostname):
        reason = _is_disallowed(address)
        if reason:
            raise MCPEndpointBlocked(
                f"MCP url '{url}' resolves to {address} ({reason}), which is not "
                "permitted. Add the host to MCP_ALLOWED_HOSTS to allow it "
                "deliberately."
            )

    return url
