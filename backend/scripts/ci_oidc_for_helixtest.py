"""Minimal OIDC discovery + JWKS for HelixTest CI against BioResearch Assistant.

Starts an HTTP server on 127.0.0.1 serving:
  - ``/.well-known/openid-configuration``
  - ``/jwks``

``AuthService`` in the app resolves JWKS from this issuer and validates RS256 JWTs.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _int_to_base64url(num: int) -> str:
    length = (num.bit_length() + 7) // 8
    data = num.to_bytes(length, byteorder="big")
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _prepare_state(issuer: str, audience: str, state_dir: Path) -> str:
    """Generate RSA keypair, JWKS, and return a signed bearer JWT."""
    state_dir.mkdir(parents=True, exist_ok=True)
    kid = "ci-helixtest"

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    (state_dir / "private.pem").write_bytes(private_pem)

    numbers = private_key.public_key().public_numbers()
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": kid,
                "use": "sig",
                "alg": "RS256",
                "n": _int_to_base64url(numbers.n),
                "e": _int_to_base64url(numbers.e),
            },
        ],
    }
    (state_dir / "jwks.json").write_text(json.dumps(jwks), encoding="utf-8")

    claims = {
        "sub": "helixtest-ci-user",
        "aud": audience,
        "email": "contact@synapticfour.com",
        "ga4gh_passport_v1": [],
    }
    token: str = jwt.encode(
        claims,
        private_pem,
        algorithm="RS256",
        headers={"kid": kid},
    )
    (state_dir / "bearer.token").write_text(token.strip(), encoding="utf-8")
    meta = {
        "issuer": issuer,
        "audience": audience,
        "kid": kid,
    }
    (state_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return token


def _run_server(host: str, port: int, issuer: str, state_dir: Path) -> None:
    jwks_body = (state_dir / "jwks.json").read_bytes()
    discovery = {
        "issuer": issuer,
        "jwks_uri": f"{issuer.rstrip('/')}/jwks",
        "authorization_endpoint": f"{issuer.rstrip('/')}/authorize",
        "token_endpoint": f"{issuer.rstrip('/')}/token",
    }
    discovery_body = json.dumps(discovery).encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: object) -> None:
            return

        def do_GET(self) -> None:
            if self.path.rstrip("/") == "/.well-known/openid-configuration":
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(discovery_body)))
                self.end_headers()
                self.wfile.write(discovery_body)
                return
            if self.path.rstrip("/") == "/jwks":
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(jwks_body)))
                self.end_headers()
                self.wfile.write(jwks_body)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

    server = HTTPServer((host, port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path("/tmp/bioresearch_oidc_ci"),
        help="Directory for keys and JWKS (default: /tmp/bioresearch_oidc_ci)",
    )
    parser.add_argument(
        "--issuer",
        default="http://127.0.0.1:8199",
        help="OIDC issuer URL (must match OIDC_ISSUER in app env)",
    )
    parser.add_argument(
        "--audience",
        default="helixtest-audience",
        help="JWT audience (must match OIDC_CLIENT_ID in app env)",
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=8199,
        help="Port for discovery/JWKS HTTP server",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Only generate keys and print bearer token to stdout, then exit",
    )
    args = parser.parse_args()

    issuer: str = args.issuer.rstrip("/")
    if args.prepare_only:
        token = _prepare_state(issuer, args.audience, args.state_dir)
        sys.stdout.write(token)
        sys.stdout.write("\n")
        return 0

    _prepare_state(issuer, args.audience, args.state_dir)
    _run_server("127.0.0.1", args.listen_port, issuer, args.state_dir)

    sys.stderr.write(
        f"ci_oidc_for_helixtest: listening on 127.0.0.1:{args.listen_port} issuer={issuer}\n",
    )
    sys.stderr.flush()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
