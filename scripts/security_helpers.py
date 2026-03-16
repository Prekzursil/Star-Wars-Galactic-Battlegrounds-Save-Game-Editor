from __future__ import annotations

import ipaddress
import json
import urllib.request
from collections.abc import Mapping
from urllib.parse import urlparse, urlunparse


def normalize_https_url(
    raw_url: str,
    *,
    allowed_hosts: set[str] | None = None,
    allowed_host_suffixes: set[str] | None = None,
    strip_query: bool = False,
) -> str:
    """Validate user-provided URLs for CLI scripts.

    Rules:
    - https scheme only,
    - no embedded credentials,
    - reject localhost/private/link-local IP targets,
    - optional hostname allowlist.
    - optional hostname suffix allowlist.
    """

    parsed = urlparse((raw_url or "").strip())
    if parsed.scheme != "https":
        raise ValueError(f"Only https URLs are allowed: {raw_url!r}")
    if not parsed.hostname:
        raise ValueError(f"URL is missing a hostname: {raw_url!r}")
    if parsed.username or parsed.password:
        raise ValueError(f"URL credentials are not allowed: {raw_url!r}")

    hostname = parsed.hostname.lower().strip(".")
    if allowed_hosts is not None and hostname not in {host.lower().strip(".") for host in allowed_hosts}:
        raise ValueError(f"URL host is not in allowlist: {hostname}")
    if allowed_host_suffixes is not None:
        suffixes = {suffix.lower().strip(".") for suffix in allowed_host_suffixes if suffix.strip(".")}
        if suffixes and not any(hostname == suffix or hostname.endswith(f".{suffix}") for suffix in suffixes):
            raise ValueError(f"URL host is not in suffix allowlist: {hostname}")

    try:
        ip_value = ipaddress.ip_address(hostname)
    except ValueError:
        ip_value = None

    if ip_value is not None and (
        ip_value.is_private
        or ip_value.is_loopback
        or ip_value.is_link_local
        or ip_value.is_reserved
        or ip_value.is_multicast
    ):
        raise ValueError(f"Private or local addresses are not allowed: {hostname}")

    if hostname in {"localhost", "localhost.localdomain"}:
        raise ValueError("Localhost URLs are not allowed.")

    sanitized = parsed._replace(fragment="", params="")
    if strip_query:
        sanitized = sanitized._replace(query="")
    return urlunparse(sanitized)


def request_https_json(
    raw_url: str,
    *,
    headers: Mapping[str, str] | None = None,
    method: str = "GET",
    data: bytes | None = None,
    allowed_hosts: set[str] | None = None,
    allowed_host_suffixes: set[str] | None = None,
    strip_query: bool = False,
    timeout: float = 30.0,
) -> tuple[object, dict[str, str]]:
    """Fetch JSON from a validated HTTPS endpoint only."""

    safe_url = normalize_https_url(
        raw_url,
        allowed_hosts=allowed_hosts,
        allowed_host_suffixes=allowed_host_suffixes,
        strip_query=strip_query,
    )
    request = urllib.request.Request(
        safe_url,
        headers=dict(headers or {}),
        method=method,
        data=data,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
        body = json.loads(response.read().decode("utf-8"))
        response_headers = {key.lower(): value for key, value in response.headers.items()}
    return body, response_headers
