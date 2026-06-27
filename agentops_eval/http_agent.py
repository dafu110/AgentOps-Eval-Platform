from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser(description="HTTP adapter for real agents.")
    parser.add_argument("--url", required=True, help="Agent HTTP endpoint.")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--input-field", default="input")
    parser.add_argument("--output-field", default="output")
    parser.add_argument("--header", action="append", default=[], help="HTTP header as Name:Value. Repeatable.")
    args = parser.parse_args()

    prompt = sys.stdin.read()
    payload = json.dumps({args.input_field: prompt}).encode("utf-8")
    headers = {"Content-Type": "application/json", **_parse_headers(args.header)}
    request = Request(args.url, data=payload, headers=headers, method="POST")

    try:
        with urlopen(request, timeout=args.timeout) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        sys.stderr.write(f"HTTP {exc.code}: {exc.reason}\n")
        return 1
    except URLError as exc:
        sys.stderr.write(f"HTTP adapter error: {exc.reason}\n")
        return 1

    try:
        record = json.loads(body)
    except json.JSONDecodeError:
        print(body)
        return 0

    output = record.get(args.output_field)
    if output is None:
        sys.stderr.write(f"Response JSON missing output field {args.output_field!r}\n")
        return 1
    print(output)
    return 0


def _parse_headers(values: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for value in values:
        if ":" not in value:
            raise SystemExit(f"Invalid header {value!r}; expected Name:Value")
        name, header_value = value.split(":", 1)
        headers[name.strip()] = header_value.strip()
    return headers


if __name__ == "__main__":
    raise SystemExit(main())
