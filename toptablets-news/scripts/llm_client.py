"""
llm_client.py - Dual-mode LLM interface for TopTablets.in news generation.
Connects to local Ollama (Gemma 2 / Qwen 2.5) with graceful fallback to template-based synthesizer.
"""
import os
import json
import logging
import requests
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOG_DIR = os.path.join(BASE_DIR, "data", "logs")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "pipeline.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("llm_client")


class LLMClient:
    def __init__(self, host: str = "http://localhost:11434", model: str = "gemma2:2b"):
        self.host = host
        self.model = model

    def is_ollama_available(self) -> bool:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def generate_json(self, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        """Attempt generation via Ollama local model, with fallback to structured editorial synthesizer."""
        if self.is_ollama_available():
            try:
                logger.info(f"Generating article via Ollama ({self.model})...")
                payload = {
                    "model": self.model,
                    "prompt": f"{system_prompt}\n\nTask Input:\n{prompt}",
                    "stream": False,
                    "format": "json"
                }
                res = requests.post(f"{self.host}/api/generate", json=payload, timeout=90)
                if res.status_code == 200:
                    text_resp = res.json().get("response", "")
                    return json.loads(text_resp)
            except Exception as e:
                logger.warning(f"Ollama generation failed or timed out: {e}")

        logger.info("Using built-in Editorial Template Synthesizer (Ollama offline or parsing fallback)...")
        return None
