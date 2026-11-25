"""Public-source HTTP only; gateway and Telegram authentication use separate clients."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

import httpx


def public_url(url: str) -> tuple[str, ...]:
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in {None, 80, 443}
    ):
        raise ValueError("unsupported public source URL")
    try:
        rows = socket.getaddrinfo(
            parsed.hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except OSError:
        raise ValueError("public source host cannot be resolved") from None
    addresses = tuple(dict.fromkeys(row[4][0] for row in rows))
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError("source host is not public")
    return addresses


class PublicTransport(httpx.BaseTransport):
    """Pin connections to checked addresses, preserving Host and TLS identity.

    Each logical origin gets a separate pool even when origins share an IP, so
    TLS connections cannot be reused across different certificate identities.
    Redirects pass through handle_request and are independently checked.
    """

    def __init__(self):
        self._transports: dict[tuple, httpx.HTTPTransport] = {}

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        address = public_url(str(request.url))[0]
        origin = (request.url.scheme, request.url.host, request.url.port, address)
        if origin not in self._transports:
            self._transports[origin] = httpx.HTTPTransport(retries=0, trust_env=False)
        headers = request.headers.copy()
        headers["Host"] = request.url.netloc.decode("ascii")
        pinned = httpx.Request(
            request.method,
            request.url.copy_with(host=address),
            headers=headers,
            stream=request.stream,
            extensions={**request.extensions, "sni_hostname": request.url.host},
        )
        return self._transports[origin].handle_request(pinned)

    def close(self):
        for transport in self._transports.values():
            transport.close()
        self._transports.clear()


def public_client(**kwargs) -> httpx.Client:
    headers = {"Accept-Encoding": "identity", **kwargs.pop("headers", {})}
    return httpx.Client(
        transport=PublicTransport(), trust_env=False, max_redirects=5, headers=headers, **kwargs
    )


def readable_encoding(response: httpx.Response) -> None:
    # Avoid decompression bombs before the decoded-byte budget can be applied.
    if response.headers.get("content-encoding", "identity").lower() not in {"", "identity"}:
        raise ValueError("compressed public source response is not supported")


def bounded_get(client: httpx.Client, url: str, *, limit: int = 12_000_000, **kwargs):
    with client.stream("GET", url, **kwargs) as response:
        response.raise_for_status()
        readable_encoding(response)
        chunks = []
        size = 0
        for chunk in response.iter_bytes(chunk_size=65536):
            size += len(chunk)
            if size > limit:
                raise ValueError("source response exceeds byte budget")
            chunks.append(chunk)
        return httpx.Response(
            response.status_code,
            headers=response.headers,
            content=b"".join(chunks),
            request=response.request,
        )
