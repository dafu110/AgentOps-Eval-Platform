from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser(description="AgentFlow Studio HTTP adapter.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    prompt = sys.stdin.read().strip()
    if not prompt:
        sys.stderr.write("AgentFlow adapter received empty prompt\n")
        return 1

    try:
        token = _login_or_register(args.base_url, args.email, args.password, args.timeout)
        response = _post_json(
            f"{args.base_url.rstrip('/')}/api/generate-canvas",
            {"user_prompt": prompt, "title": "AgentOps Eval Canvas", "profile": "general"},
            args.timeout,
            {"Authorization": f"Bearer {token}"},
        )
    except AdapterError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 1

    print(json.dumps(_compact_canvas_response(response), ensure_ascii=False))
    return 0


class AdapterError(RuntimeError):
    pass


def _login_or_register(base_url: str, email: str, password: str, timeout: int) -> str:
    try:
        response = _post_json(f"{base_url.rstrip('/')}/api/auth/login", {"email": email, "password": password}, timeout)
    except AdapterError:
        response = _post_json(f"{base_url.rstrip('/')}/api/auth/register", {"email": email, "password": password}, timeout)
    token = response.get("token")
    if not isinstance(token, str) or not token:
        raise AdapterError("AgentFlow auth response missing token")
    return token


def _post_json(url: str, payload: dict, timeout: int, headers: dict[str, str] | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        raise AdapterError(f"HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise AdapterError(f"HTTP adapter error: {exc.reason}") from exc
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise AdapterError("AgentFlow response was not JSON") from exc
    if not isinstance(parsed, dict):
        raise AdapterError("AgentFlow response JSON must be an object")
    return parsed


def _compact_canvas_response(response: dict) -> dict:
    return {
        "summary": response.get("summary", ""),
        "node_count": len(response.get("nodes", [])) if isinstance(response.get("nodes"), list) else 0,
        "edge_count": len(response.get("edges", [])) if isinstance(response.get("edges"), list) else 0,
        "canvas_id": (response.get("canvas") or {}).get("id") if isinstance(response.get("canvas"), dict) else None,
    }


if __name__ == "__main__":
    raise SystemExit(main())
