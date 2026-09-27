import httpx
import json
import time

def test():
    print("Testing Ollama generate with 120s timeout...")
    start = time.time()
    payload = {
        "model": "qwen2.5-coder:7b-instruct",
        "prompt": "You are an autonomous browser agent. Return JSON: {\"thought\": \"Navigating to homepage\", \"action\": \"navigate\", \"url\": \"http://localhost:3000\"}",
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 150
        }
    }
    try:
        r = httpx.post("http://localhost:11434/api/generate", json=payload, timeout=120.0)
        elapsed = time.time() - start
        print(f"Status: {r.status_code}, Elapsed: {elapsed:.2f}s")
        data = r.json()
        print("Response:", data.get("response"))
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test()
