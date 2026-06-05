"""KigurumiAgent 的环境变量配置。

使用两个 OpenAI 兼容客户端:
- image_client: 图像生成/编辑(默认 GPT-Image-2,OpenAI 官方端点)。
- reason_client: 推理 / 视觉评审(默认走阿里云百炼 Dashscope OpenAI 兼容接口)。
  注意:由于 _review / _vision_pick / _final_pick 会向该模型发送 image_url 块,
  REASON_MODEL 必须是支持视觉的模型(如 qwen-vl-max-latest / qwen3-vl-plus);
  纯文本模型会忽略或拒绝图像输入。

两个端点都可以通过 *_BASE_URL 重定向到任意 OpenAI 兼容网关。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT / "dataset"
OUTPUT_DIR = ROOT / "outputs"

try:
    from dotenv import load_dotenv  # type: ignore
    # 先尝试仓库根的 .env,再回退到 notebook/.env(兼容原有放置位置)
    for candidate in (ROOT / ".env", Path(__file__).resolve().parent / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)
except Exception:
    pass


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
        n=int(os.environ.get("IMAGE_N", "1")),
    )
    reason = ReasonConfig(
        api_key=_need("REASON_API_KEY"),
        base_url=os.environ.get(
            "REASON_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ).rstrip("/"),
        model=os.environ.get("REASON_MODEL", "qwen3.6-plus"),
    )
    return AgentConfig(
        image=image,
        reason=reason,
        max_refine=int(os.environ.get("MAX_REFINE", "2")),
        similar_top_k=int(os.environ.get("SIMILAR_TOP_K", "2")),
    )
