from __future__ import absolute_import, annotations, division

import ipaddress
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from email.message import Message
from typing import Dict, Mapping, Optional, Set, Tuple
from urllib.parse import urlparse, urlunparse

_LOCAL_IP_FLAGS = ("is_private", "is_loopback", "is_link_local", "is_reserved", "is_multicast")


def _parse_https_url(raw_url: str):
    parsed = urlparse((raw_url or "").strip())
    if parsed.scheme != "https":
        raise ValueError(f"Only https URLs are allowed: {raw_url!r}")
    if not parsed.hostname:
        raise ValueError(f"URL is missing a hostname: {raw_url!r}")
    if parsed.username or parsed.password:
        raise ValueError(f"URL credentials are not allowed: {raw_url!r}")
    return parsed


def _normalized_hosts(values: Optional[Set[str]]) -> Set[str]:
    if not values:
        return set()
    return {value.lower().strip(".") for value in values if value.strip(".")}


def _hostname_matches_suffix(hostname: str, suffixes: Set[str]) -> bool:
    return any(hostname == suffix or hostname.endswith(f".{suffix}") for suffix in suffixes)


def _validate_hostname_allowlists(
    hostname: str,
    *,
    allowed_hosts: Optional[Set[str]] = None,
    allowed_host_suffixes: Optional[Set[str]] = None,
) -> None:
    exact_hosts = _normalized_hosts(allowed_hosts)
    if exact_hosts and hostname not in exact_hosts:
        raise ValueError(f"URL host is not in allowlist: {hostname}")

    suffixes = _normalized_hosts(allowed_host_suffixes)
    if suffixes and not _hostname_matches_suffix(hostname, suffixes):
        raise ValueError(f"URL host is not in suffix allowlist: {hostname}")


def _is_local_or_private_ip(hostname: str) -> bool:
    try:
        ip_value = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return any(bool(getattr(ip_value, flag)) for flag in _LOCAL_IP_FLAGS)


def _reject_local_targets(hostname: str) -> None:
    if _is_local_or_private_ip(hostname):
        raise ValueError(f"Private or local addresses are not allowed: {hostname}")
    if hostname in {"localhost", "localhost.localdomain"}:
        raise ValueError("Localhost URLs are not allowed.")


def normalize_https_url(
    raw_url: str,
    *,
    allowed_hosts: Optional[Set[str]] = None,
    allowed_host_suffixes: Optional[Set[str]] = None,
    strip_query: bool = False,
) -> str:
    """Validate user-provided URLs for CLI scripts."""

    parsed = _parse_https_url(raw_url)
    hostname = parsed.hostname.lower().strip(".")
    _validate_hostname_allowlists(
        hostname,
        allowed_hosts=allowed_hosts,
        allowed_host_suffixes=allowed_host_suffixes,
    )
    _reject_local_targets(hostname)

    sanitized = parsed._replace(fragment="", params="")
    if strip_query:
        sanitized = sanitized._replace(query="")
    return urlunparse(sanitized)


def _build_request_target(path: str, query: Dict[str, str]) -> str:
    query_text = urllib.parse.urlencode(query, doseq=False)
    return path + (f"?{query_text}" if query_text else "")


def _build_json_decode_error(exc: UnicodeDecodeError) -> ValueError:
    _ = exc
    return ValueError("Response body is not valid UTF-8 JSON.")


def _secure_ssl_context() -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_default_certs(purpose=ssl.Purpose.SERVER_AUTH)
    return context


def _read_https_success(response) -> Tuple[int, str, str, Dict[str, str]]:
    raw_body = response.read().decode("utf-8")
    response_headers = {str(key).lower(): str(value) for key, value in response.headers.items()}
    status = int(getattr(response, "status", response.getcode()))
    reason = str(getattr(response, "reason", "") or "HTTP error")
    return status, reason, raw_body, response_headers


def _read_https_error(exc: urllib.error.HTTPError) -> Tuple[int, str, str, Dict[str, str]]:
    raw_body = exc.read().decode("utf-8", errors="replace") if exc.fp is not None else ""
    error_headers = tuple(exc.headers.items()) if exc.headers else ()
    response_headers = {str(key).lower(): str(value) for key, value in error_headers}
    status = int(exc.code)
    reason = str(exc.reason or "HTTP error")
    return status, reason, raw_body, response_headers


def _build_https_request(
    *,
    host: str,
    method: str,
    request_target: str,
    headers: Dict[str, str],
    data: Optional[bytes],
) -> urllib.request.Request:
    return urllib.request.Request(
        url=f"https://{host}{request_target}",
        data=data,
        headers=headers,
        method=method.upper(),
    )


def _open_https_request(
    request: urllib.request.Request,
    timeout: float,
) -> Tuple[int, str, str, Dict[str, str]]:
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=_secure_ssl_context()))
    with opener.open(request, timeout=timeout) as response:
        return _read_https_success(response)


def _execute_https_request(
    *,
    host: str,
    method: str,
    request_target: str,
    headers: Dict[str, str],
    data: Optional[bytes],
    timeout: float,
) -> Tuple[int, str, str, Dict[str, str]]:
    request = _build_https_request(
        host=host,
        method=method,
        request_target=request_target,
        headers=headers,
        data=data,
    )
    try:
        return _open_https_request(request, timeout)
    except urllib.error.HTTPError as exc:
        return _read_https_error(exc)


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
    parsed = urllib.parse.urlparse(safe_url)
    host = (parsed.hostname or "").strip().lower()
    path = parsed.path or "/"
    query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=False)
    query = {str(key): str(value) for key, value in query_pairs}
    request_target = _build_request_target(path, query)
    status, reason, raw_body, response_headers = _execute_https_request(
        host=host,
        method=method,
        request_target=request_target,
        headers=dict(headers or {}),
        data=data,
        timeout=timeout,
    )
    if not 200 <= status < 300:
        error_headers = Message()
        for header_name, header_value in response_headers.items():
            error_headers[header_name] = header_value
        raise urllib.error.HTTPError(
            url=f"https://{host}{request_target}",
            code=status,
            msg=reason,
            hdrs=error_headers,
            fp=None,
        )

    try:
        return json.loads(raw_body), response_headers
    except UnicodeDecodeError as exc:
        raise _build_json_decode_error(exc) from exc
