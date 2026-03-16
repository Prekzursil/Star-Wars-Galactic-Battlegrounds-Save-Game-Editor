from __future__ import absolute_import

import http.client
import ipaddress
import json
from collections.abc import Mapping
from typing import Dict, Optional, Set, Tuple
from urllib import error as urllib_error
from urllib.parse import urlparse, urlunparse


def normalize_https_url(
    raw_url: str,
    *,
    allowed_hosts: Optional[Set[str]] = None,
    allowed_host_suffixes: Optional[Set[str]] = None,
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
    headers: Optional[Mapping[str, str]] = None,
    method: str = "GET",
    data: Optional[bytes] = None,
    allowed_hosts: Optional[Set[str]] = None,
    allowed_host_suffixes: Optional[Set[str]] = None,
    strip_query: bool = False,
    timeout: float = 30.0,
) -> Tuple[object, Dict[str, str]]:
    """Fetch JSON from a validated HTTPS endpoint only."""

    safe_url = normalize_https_url(
        raw_url,
        allowed_hosts=allowed_hosts,
        allowed_host_suffixes=allowed_host_suffixes,
        strip_query=strip_query,
    )
    parsed = urlparse(safe_url)
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Validated URL is missing a hostname.")
    request_path = parsed.path or "/"
    if parsed.query:
        request_path = f"{request_path}?{parsed.query}"

    connection = http.client.HTTPSConnection(hostname, parsed.port, timeout=timeout)
    request_headers = dict(headers or {})
    if data is not None and "Content-Length" not in request_headers:
        request_headers["Content-Length"] = str(len(data))
    connection.request(method, request_path, body=data, headers=request_headers)
    response = connection.getresponse()
    try:
        response_body = response.read()
        response_message = response.msg
        response_headers = {key.lower(): value for key, value in response.getheaders()}
    finally:
        connection.close()

    if response.status >= 400:
        raise urllib_error.HTTPError(
            safe_url,
            response.status,
            response.reason,
            response_message,
            None,
        )

    try:
        body = json.loads(response_body.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError("Response body is not valid UTF-8 JSON.") from exc
    return body, response_headers
