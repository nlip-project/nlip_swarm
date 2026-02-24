import json
import os
import urllib.error
import urllib.request

# Edit this payload directly when testing different chat properties.
CHAT_PAYLOAD = {
    "model": "",
    "messages": [
        {"role": "user", "content": "What's the capital of France?"},
    ],
}

# Fallback payload for /completions if /chat/completions is unavailable.
COMPLETION_PAYLOAD = {
    "model": "",
    "prompt": "What's the capital of France?",
}


def main() -> None:
    base = os.environ.get("OLLAMA_URL", "").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "")

    print("OLLAMA_URL:", base)
    print("OLLAMA_MODEL:", model)

    if not base:
        raise SystemExit("OLLAMA_URL is not set")
    if not model:
        raise SystemExit("OLLAMA_MODEL is not set")

    models_url = f"{base}/models"
    print("models url:", models_url)
    with urllib.request.urlopen(models_url) as response:
        print("models:", response.read().decode("utf-8")[:500])

    chat_payload = dict(CHAT_PAYLOAD)
    chat_payload["model"] = chat_payload.get("model") or model

    def post_json(url: str, payload: dict) -> str:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as response:
            return response.read().decode("utf-8")[:500]

    chat_urls = [
        f"{base}/chat/completions",
        f"{base.replace('/engines/v1', '/engines/llama.cpp/v1')}/chat/completions",
    ]

    for url in chat_urls:
        print("trying chat url:", url)
        try:
            print("chat url used:", url)
            print("chat:", post_json(url, chat_payload))
            return
        except urllib.error.HTTPError as exc:
            print(f"chat url failed ({exc.code}):", url)
            if exc.code != 404:
                raise

    completion_payload = dict(COMPLETION_PAYLOAD)
    completion_payload["model"] = completion_payload.get("model") or model
    completion_url = f"{base}/completions"
    print("completion url:", completion_url)
    print("completion:", post_json(completion_url, completion_payload))


if __name__ == "__main__":
    main()
