"""Environment-driven config for the Kigurumi agent.

Two OpenAI-compatible clients are used:
- image_client: GPT-Image-2 for generation/editing (OpenAI).
- reason_client: Qwen3.5 VL via Aliyun Dashscope's OpenAI-compatible endpoint.

Both can be redirected via env vars to any OpenAI-compatible gateway.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT / "dataset"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


@dataclass(frozen=True)
class ImageConfig:
    api_key: str
    base_url: str
    model: str
    size: str
    quality: str
    n: int


@dataclass(frozen=True)
class ReasonConfig:
    api_key: str
    base_url: str
    model: str


@dataclass(frozen=True)
class AgentConfig:
    image: ImageConfig
    reason: ReasonConfig
    max_refine: int
    similar_top_k: int


def _need(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Missing env var: {name}. Copy notebook/.env.example to .env and fill it in.")
    return value


def load_config() -> AgentConfig:
    image = ImageConfig(
        api_key=_need("IMAGE_API_KEY"),
        base_url=os.environ.get("IMAGE_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        model=os.environ.get("IMAGE_MODEL", "gpt-image-2"),
        size=os.environ.get("IMAGE_SIZE", "1024x1024"),
        quality=os.environ.get("IMAGE_QUALITY", "high"),
        n=int(os.environ.get("IMAGE_N", "2")),
    )
    reason = ReasonConfig(
        api_key=_need("REASON_API_KEY"),
        base_url=os.environ.get(
            "REASON_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ).rstrip("/"),
        model=os.environ.get("REASON_MODEL", "qwen-vl-max-latest"),
    )
    return AgentConfig(
        image=image,
        reason=reason,
        max_refine=int(os.environ.get("MAX_REFINE", "2")),
        similar_top_k=int(os.environ.get("SIMILAR_TOP_K", "2")),
    )
