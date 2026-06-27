from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser(description="Big Data Analytics Agent multipart adapter.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--sample-file", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--workflow", default="")
    args = parser.parse_args()

    prompt = sys.stdin.read().strip()
    if not args.sample_file.exists():
        sys.stderr.write(f"Sample file not found: {args.sample_file}\n")
        return 1

    workflow = {"eval_prompt": prompt}
    if args.workflow:
        workflow.update(json.loads(args.workflow))

    try:
        response = _post_multipart(args.url, args.sample_file, workflow, args.timeout)
    except AdapterError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 1

    print(json.dumps(_compact_analysis_response(response), ensure_ascii=False))
    return 0


class AdapterError(RuntimeError):
    pass


def _post_multipart(url: str, sample_file: Path, workflow: dict, timeout: int) -> dict:
    boundary = f"----agentops-{uuid.uuid4().hex}"
    content_type = mimetypes.guess_type(sample_file.name)[0] or "text/csv"
    body = b"".join(
        [
            _field(boundary, "workflow", json.dumps(workflow)),
            _file_field(boundary, "file", sample_file.name, content_type, sample_file.read_bytes()),
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    request = Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        raise AdapterError(f"HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise AdapterError(f"HTTP adapter error: {exc.reason}") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AdapterError("BigData response was not JSON") from exc
    if not isinstance(parsed, dict):
        raise AdapterError("BigData response JSON must be an object")
    return parsed


def _field(boundary: str, name: str, value: str) -> bytes:
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
        f"{value}\r\n"
    ).encode("utf-8")


def _file_field(boundary: str, name: str, filename: str, content_type: str, data: bytes) -> bytes:
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    return header + data + b"\r\n"


def _compact_analysis_response(response: dict) -> dict:
    return {
        "job_id": response.get("job_id"),
        "summary": response.get("executive_summary") or response.get("summary") or "",
        "recommendation_count": len(response.get("recommendations", [])) if isinstance(response.get("recommendations"), list) else 0,
        "chart_count": len(response.get("charts", [])) if isinstance(response.get("charts"), list) else 0,
        "sql_valid": (response.get("sql_audit") or {}).get("validation_status") if isinstance(response.get("sql_audit"), dict) else None,
    }


if __name__ == "__main__":
    raise SystemExit(main())
