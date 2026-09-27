import httpx
import json

def test_ollama():
    payload = {
        "model": "qwen2.5-coder:7b-instruct",
        "prompt": 'You are a QA Agent. Respond ONLY with valid JSON: {"thought": "I will navigate to the home page", "action": "navigate", "params": {"url": "http://localhost:3000"}}',
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1}
    }
    print("Testing connection to Ollama at http://localhost:11434 with model qwen2.5-coder:7b-instruct ...")
    r = httpx.post("http://localhost:11434/api/generate", json=payload, timeout=60.0)
    print("Status Code:", r.status_code)
    response_text = r.json().get("response")
    print("LLM Response Text:", response_text)
    parsed = json.loads(response_text)
    print("Parsed JSON successfully:", parsed)

if __name__ == "__main__":
    test_ollama()
