import socket

import httpx
import pytest

from ai_dash.network import PublicTransport, bounded_get, public_client, public_url


def dns(*addresses):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443)) for ip in addresses]


@pytest.mark.parametrize(
    "addresses",
    [(), ("127.0.0.1",), ("169.254.169.254",), ("10.0.0.1",), ("8.8.8.8", "::1")],
)
def test_private_or_mixed_dns_answers_never_connect(monkeypatch, addresses):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: dns(*addresses))
    monkeypatch.setattr(httpx, "HTTPTransport", lambda **kw: pytest.fail("must not connect"))
    with PublicTransport() as transport, pytest.raises(ValueError, match="not public"):
        transport.handle_request(httpx.Request("GET", "https://publisher.example/feed"))


def test_pins_validated_ip_and_keeps_host_tls_identity_and_origin_pools(monkeypatch):
    resolutions = []
    requests = []
    pools = []

    def resolve(host, port, **kw):
        resolutions.append((host, port))
        # A second resolution for this hostname would be a rebinding attack.
        return dns("8.8.8.8")

    class Wire(httpx.BaseTransport):
        def __init__(self, **kwargs):
            assert kwargs == {"retries": 0, "trust_env": False}
            self.closed = False
            pools.append(self)

        def handle_request(self, request):
            requests.append(request)
            assert request.url.host == "8.8.8.8"
            return httpx.Response(200, content=b"public evidence")

        def close(self):
            self.closed = True

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    monkeypatch.setattr(httpx, "HTTPTransport", Wire)
    with public_client() as client:
        for host in ("one.example", "two.example", "one.example"):
            assert client.get(f"https://{host}/feed").text == "public evidence"
    assert len(resolutions) == 3  # once per logical request; wire receives an IP
    assert len(pools) == 2  # origins sharing one IP cannot share a TLS pool
    assert all(pool.closed for pool in pools)
    assert [r.headers["host"] for r in requests] == ["one.example", "two.example", "one.example"]
    assert requests[0].extensions["sni_hostname"] == "one.example"
    assert requests[0].headers["accept-encoding"] == "identity"


def test_redirect_to_private_service_is_rejected_before_second_connection(monkeypatch):
    sent = []
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, *a, **k: dns("127.0.0.1" if host == "internal.example" else "8.8.8.8"),
    )

    class Wire(httpx.BaseTransport):
        def __init__(self, **kwargs):
            pass

        def handle_request(self, request):
            sent.append(request)
            return httpx.Response(302, headers={"location": "http://internal.example/private"})

    monkeypatch.setattr(httpx, "HTTPTransport", Wire)
    with public_client(follow_redirects=True) as client:
        with pytest.raises(ValueError, match="not public"):
            bounded_get(client, "https://publisher.example/feed")
    assert len(sent) == 1


def test_body_budget_stops_stream_and_closes_connection():
    class Body(httpx.SyncByteStream):
        closed = False
        yielded = 0

        def __iter__(self):
            for _ in range(100):
                self.yielded += 1
                yield b"x" * 65536

        def close(self):
            self.closed = True

    body = Body()
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, stream=body))
    ) as client:
        with pytest.raises(ValueError, match="byte budget"):
            bounded_get(client, "https://publisher.example/feed", limit=65536)
    assert body.closed and body.yielded == 2


def test_rejects_compression_before_reading_body():
    class Body(httpx.SyncByteStream):
        def __iter__(self):
            pytest.fail("compressed body must not be decoded")
            yield b""

    with httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, headers={"content-encoding": "gzip"}, stream=Body())
        )
    ) as client:
        with pytest.raises(ValueError, match="compressed"):
            bounded_get(client, "https://publisher.example/feed")


def test_dns_failure_does_not_expose_resolver_error(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("private resolver diagnostics")

    monkeypatch.setattr(socket, "getaddrinfo", fail)
    with pytest.raises(ValueError, match="cannot be resolved") as caught:
        public_url("https://publisher.example/")
    assert "private resolver" not in str(caught.value)
