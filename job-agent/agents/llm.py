"""Thin LLM client: Anthropic Messages API over plain HTTP (no SDK needed) + an offline mock."""
import json
import os
import time

import requests

# Models that accept the effort setting and server-side refusal fallbacks used below.
CURRENT_MODELS = ("claude-sonnet-5-5", "claude-opus-5-5")


class LLM:
    def __init__(self, cfg: dict, key: str = ""):
        self.provider = cfg.get("provider", "anthropic")
        self.model = cfg.get("model", "claude-sonnet-5-5")
        self.key = key or os.environ.get(cfg.get("api_key_env", "ANTHROPIC_API_KEY"), "").strip()
        if self.provider == "anthropic" and not self.key:
            raise SystemExit("ANTHROPIC_API_KEY is not set in this terminal.\n"
                             "Set it (see SETUP.md), or run 'python run.py find' to search without AI.")

    def json(self, system: str, prompt: str, schema: dict) -> dict:
        """Ask for a JSON object that follows `schema`."""
        if self.provider == "mock":
            return _mock(prompt)
        headers = {"x-api-key": self.key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        body = {
            "model": self.model,
            # Thinking counts towards max_tokens, so leave plenty of room or the answer is cut off.
            "max_tokens": 16000,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
            "output_config": {"format": {"type": "json_schema", "schema": schema}},
        }
        if self.model in CURRENT_MODELS:
            body["output_config"]["effort"] = "medium"
            body["fallbacks"] = "default"
            headers["anthropic-beta"] = "server-side-fallback-2026-07-01"

        for attempt in range(4):
            r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=600)
            if r.status_code not in (429, 500, 502, 503, 529) or attempt == 3:
                break
            time.sleep(5 * 2 ** attempt)
        if r.status_code == 401:
            raise SystemExit("The API key was rejected. Create a new key at console.anthropic.com and set it again.")
        if r.status_code >= 400:
            try:
                message = r.json()["error"]["message"]
            except (ValueError, KeyError):
                message = r.text[:300]
            if r.status_code in (400, 403, 404):  # same for every job (billing, model name...): stop now
                raise SystemExit(f"Anthropic API error {r.status_code}: {message}")
            raise RuntimeError(f"Anthropic API error {r.status_code}: {message}")

        data = r.json()
        if data.get("stop_reason") != "end_turn":
            raise RuntimeError(f"AI reply was not complete (stop_reason={data.get('stop_reason')})")
        return json.loads("".join(b["text"] for b in data["content"] if b.get("type") == "text"))


def _mock(prompt: str) -> dict:
    """Fixed fake answers so the pipeline can be tested without an API key."""
    if "TASK: FIT" in prompt:
        return {"fit_score": 82, "reasons": ["DEMO: not a real assessment"], "gaps": ["DEMO"],
                "keywords": [".NET", "Azure", "microservices", "architecture"]}
    note = ("[DEMO PLACEHOLDER - NOT AI GENERATED] This text only shows where the cover letter goes. "
            "Set ANTHROPIC_API_KEY and run 'python run.py hunt' to get a real, job-specific letter.")
    return {"headline": "", "summary": "", "skills_order": [], "experience": [], "projects": [],
            "rewrites": [], "cover_letter_paragraphs": [note]}
