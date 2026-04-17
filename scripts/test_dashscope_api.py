#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from urllib import error, request

from dotenv import load_dotenv


DEFAULT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"


def load_env():
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")
    return project_root


def build_payload(question):
    model = os.getenv("DASHSCOPE_MODEL", "qwen-plus").strip() or "qwen-plus"
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question},
        ],
        "temperature": 0.7,
    }


def main():
    project_root = load_env()
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    api_url = os.getenv("DASHSCOPE_API_URL", DEFAULT_URL).strip() or DEFAULT_URL
    question = " ".join(sys.argv[1:]).strip() or "你好"

    print(f"Project root: {project_root}")
    print(f"API URL: {api_url}")
    print(f"Model: {os.getenv('DASHSCOPE_MODEL', 'qwen-plus')}")
    print(f"Question: {question}")

    if not api_key:
        print("Error: `.env` 中没有读取到 DASHSCOPE_API_KEY。")
        sys.exit(1)

    payload = build_payload(question)
    req = request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            data = json.loads(body)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP Error: {exc.code}")
        print(body)
        sys.exit(2)
    except error.URLError as exc:
        print(f"Network Error: {exc}")
        sys.exit(3)
    except json.JSONDecodeError as exc:
        print(f"JSON Decode Error: {exc}")
        sys.exit(4)

    answer = data.get("choices", [{}])[0].get("message", {}).get("content")
    if not answer:
        print("Request succeeded, but no model reply was found in the response:")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        sys.exit(5)

    print("Request succeeded.")
    print("Model reply:")
    print(answer)


if __name__ == "__main__":
    main()
