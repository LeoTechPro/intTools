from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description="Call intData Agent Tool Plane from Agno/local harness.")
    parser.add_argument("--url", default=os.getenv("AGENT_PLANE_URL", "http://127.0.0.1:9192"))
    parser.add_argument("--facade", default="agno", choices=["agno", "openclaw", "codex_app"])
    parser.add_argument("--principal-json", default='{"id":"agno-local"}')
    parser.add_argument("--tool", required=True)
    parser.add_argument("--args-json", default="{}")
    parser.add_argument("--approval-ref")
    args = parser.parse_args()

    payload = {
        "facade": args.facade,
        "principal": json.loads(args.principal_json),
        "tool": args.tool,
        "args": json.loads(args.args_json),
    }
    if args.approval_ref:
        payload["approval_ref"] = args.approval_ref

    print(json.dumps(_post(args.url.rstrip("/") + "/v1/tools/call", payload), ensure_ascii=False, indent=2))
    return 0


def _post(url: str, payload: dict) -> dict:
    request = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return json.loads(exc.read().decode("utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
