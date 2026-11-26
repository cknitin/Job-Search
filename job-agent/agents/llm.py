"""Thin LLM client: Anthropic Messages API over plain HTTP (no SDK needed) + an offline mock."""
import json
import os
import re

import requests


class LLM:
    def __init__(self, cfg: dict):
        self.provider = cfg.get("provider", "anthropic")
        self.model = cfg.get("model", "claude-sonnet-5-5")
        self.key = os.environ.get(cfg.get("api_key_env", "ANTHROPIC_API_KEY"), "")
        if self.provider == "anthropic" and not self.key:
            raise SystemExit("Set ANTHROPIC_API_KEY (or set llm.provider: mock to test offline).")

    def json(self, system: str, prompt: str, max_tokens: int = 2000) -> dict:
        """Ask for a JSON object and parse it robustly."""
        if self.provider == "mock":
            return _mock(prompt)
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": self.key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": self.model, "max_tokens": max_tokens, "system": system,
                  "messages": [{"role": "user", "content": prompt + "\n\nReturn ONLY a JSON object."}]},
            timeout=120,
        )
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json()["content"])
        m = re.search(r"\{.*\}", text, re.S)
        return json.loads(m.group(0) if m else text)


def _mock(prompt: str) -> dict:
    """Deterministic fake responses so the whole pipeline can be tested without an API key."""
    if "TASK: FIT" in prompt:
        return {"fit_score": 82, "reasons": ["Strong .NET/Azure match"], "gaps": ["Kubernetes depth"],
                "keywords": [".NET", "Azure", "microservices", "architecture"]}
    if "TASK: TAILOR" in prompt:
        return {"headline": "Solution Architect | .NET & Azure",
                "summary": "Solution Architect with 17+ years building .NET and Azure platforms.",
                "skills_order": ["cloud_architecture", "architecture", "languages"],
                "experience": [{"index": 0, "bullets": [0, 1, 2, 8, 10, 12]}, {"index": 1, "bullets": [0, 1]}],
                "rewrites": {}, "cover_letter": "Dear Hiring Team,\n\nI am excited to apply...\n\nRegards"}
    return {}
