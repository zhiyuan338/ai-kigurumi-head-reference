"""从 ../prompts/*.md 中加载各阶段的 prompt。

每个 step 的 markdown 文件交替出现 `## <小节名>` 标题和 ```text``` 围栏代码块。
本模块抽取这些围栏内容,并按稳定的英文 key 映射,以便 Agent 按名取用。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

_HEADER_TO_KEY = {
    "通用 Prompt": "general",
    "表情修正 Prompt": "expression",
    "正脸修正 Prompt": "face",
    "脸型幼态化 Prompt": "childlike",
    "头壳感不足修正 Prompt": "shell",
    "太3D/太娃娃修正 Prompt": "too3d",
    "表情跑偏修正 Prompt": "expression",
    "脸型变尖修正 Prompt": "face",
    "四面图 Prompt": "four",
    "八面图 Prompt (不使用)": "eight",
    "八面图 Prompt": "eight",
}

_SECTION_RE = re.compile(
    r"^##\s+([^\n]+?)\s*\n+```(?:text)?\n(.*?)```",
    re.DOTALL | re.MULTILINE,
)


@dataclass(frozen=True)
class StepPrompts:
    step_id: int
    general: str
    refinements: Dict[str, str]

    def refinement_keys(self) -> list[str]:
        return list(self.refinements.keys())


def _parse_step_file(path: Path) -> Dict[str, str]:
    text = path.read_text(encoding="utf-8")
    sections: Dict[str, str] = {}
    for header, body in _SECTION_RE.findall(text):
        key = _HEADER_TO_KEY.get(header.strip())
        if key is None:
            continue
        sections[key] = body.strip()
    return sections


def load_step_prompts(step_id: int) -> StepPrompts:
    filename = {
        1: "step1-head-reference.md",
        2: "step2-kigurumi-design.md",
        3: "step3-product-view.md",
    }[step_id]
    sections = _parse_step_file(PROMPTS_DIR / filename)
    if "general" not in sections and step_id == 3:
        sections["general"] = sections["four"]
    if "general" not in sections:
        raise ValueError(f"step{step_id}: missing 通用 Prompt section")
    general = sections.pop("general")
    return StepPrompts(step_id=step_id, general=general, refinements=sections)


def load_all() -> Dict[int, StepPrompts]:
    return {step_id: load_step_prompts(step_id) for step_id in (1, 2, 3)}


if __name__ == "__main__":
    for step_id, sp in load_all().items():
        print(f"step{step_id}: general={len(sp.general)} chars; refinements={sp.refinement_keys()}")
