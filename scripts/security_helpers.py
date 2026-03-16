from __future__ import absolute_import, division

import http.client
import ipaddress
import json
import socket
import ssl
from typing import Any, Dict, Mapping, Optional, Set, Tuple, cast
from urllib import error as urllib_error
from urllib.parse import urlparse, urlunparse


class _SocketResponseAdapter:
    def __init__(self, connection: ssl.SSLSocket):
        self._connection = connection

    def makefile(self, mode: str = "rb") -> Any:
        del mode
        return self._connection.makefile("rb")


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


def _build_request_bytes(
    *,
    hostname: str,
    request_target: str,
    method: str,
    headers: Dict[str, str],
    data: Optional[bytes],
) -> bytes:
    request_lines = [
        f"{method} {request_target} HTTP/1.1",
        f"Host: {hostname}",
        "Connection: close",
    ]
    for key, value in headers.items():
        request_lines.append(f"{key}: {value}")
    if data is not None and "Content-Length" not in headers:
        request_lines.append(f"Content-Length: {len(data)}")
    request_bytes = ("\r\n".join(request_lines) + "\r\n\r\n").encode("ascii")
    if data is not None:
        request_bytes += data
    return request_bytes


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
    port = parsed.port or 443
    request_target = parsed.path or "/"
    if parsed.query:
        request_target = f"{request_target}?{parsed.query}"

    ssl_context = ssl.create_default_context()
    request_headers = dict(headers or {})
    request_bytes = _build_request_bytes(
        hostname=hostname,
        request_target=request_target,
        method=method,
        headers=request_headers,
        data=data,
    )

    with socket.create_connection((hostname, port), timeout=timeout) as tcp_connection:
        with ssl_context.wrap_socket(tcp_connection, server_hostname=hostname) as tls_connection:
            tls_connection.sendall(request_bytes)
            response = http.client.HTTPResponse(cast(Any, _SocketResponseAdapter(tls_connection)))
            response.begin()
            response_body = response.read()
            response_headers = {key.lower(): value for key, value in response.getheaders()}
            response_message = response.msg
            status_code = response.status
            reason = response.reason

    if status_code >= 400:
        raise urllib_error.HTTPError(
            safe_url,
            status_code,
            reason,
            response_message,
            None,
        )

    try:
        body = json.loads(response_body.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError("Response body is not valid UTF-8 JSON.") from exc
    return body, response_headers
