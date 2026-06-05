"""KigurumiAgent: 三阶段流水线,把目标角色参考图转换成多视角 Kigurumi 商品预览。

流程:
1. Step 1 —— 去遮挡角色头部四视图(GPT-Image-2 编辑 + Qwen 视觉评审/修正)。
2. 从 dataset/ 中挑选 0-2 张视觉相似的店家成品(Qwen 先按目录名预筛,再视觉细选)。
3. Step 2 —— Kigurumi 头壳四视图(以 Step 1 最佳图 + 表情参考 + 相似成品作为参考)。
4. Step 3 —— 商品照风格四面视图(spec 指定不再做修正循环)。

每次运行产生的所有候选图、Qwen 的判定与相似成品选择都会落到 outputs/<run-id>/,
并写入 run.json 审计轨迹,方便人工回看每一轮的决策。
"""

from __future__ import annotations

import base64
import inspect
import json
import mimetypes
import re
import shutil
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

from openai import OpenAI
from openai.resources.images import Images

from config import AgentConfig, DATASET_DIR, OUTPUT_DIR
from prompts import StepPrompts, load_all


# 在 import 时一次性探出当前 openai SDK 的 images.edit 接受哪些命名参数;
# 旧版 SDK 没有 quality / size 时,会自动改走 extra_body 透传到上游 API。
_EDIT_PARAMS: set[str] = set(inspect.signature(Images.edit).parameters)


# --------------------------- 数据类 ---------------------------

@dataclass
class Candidate:
    """单张已落盘的生成结果。"""
    path: Path
    step: int
    iteration: int
    prompt_key: str
    index: int

    def as_dict(self) -> dict:
        return {**asdict(self), "path": str(self.path)}


@dataclass
class StepRun:
    step: int
    iterations: list[dict] = field(default_factory=list)
    best: Candidate | None = None

    def as_dict(self) -> dict:
        return {
            "step": self.step,
            "iterations": self.iterations,
            "best": self.best.as_dict() if self.best else None,
        }


@dataclass
class AgentResult:
    run_dir: Path
    step1: StepRun
    step2: StepRun
    step3: StepRun
    similar: list[Path]

    def as_dict(self) -> dict:
        return {
            "run_dir": str(self.run_dir),
            "step1": self.step1.as_dict(),
            "step2": self.step2.as_dict(),
            "step3": self.step3.as_dict(),
            "similar": [str(p) for p in self.similar],
        }


# --------------------------- 工具函数 ---------------------------

def _to_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCE_RE = re.compile(r"^```[a-zA-Z]*\n?", re.MULTILINE)


def _find_last_balanced_object(text: str) -> str | None:
    """扫描文本,返回最后一个左右大括号平衡的 {...} 子串。

    用于从模型回复里抠出真正的 JSON 结果,容忍前面的散文、思考片段、伪 JSON 等。
    """
    last: str | None = None
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                last = text[start : i + 1]
    return last


def _extract_json(text: str) -> dict:
    """容忍 Qwen 思考块、``` 围栏、前后散文等场景下提取 JSON 结果。"""
    text = text.strip()
    # 先剥 <think>...</think>,thinking 模式下会出现
    text = _THINK_RE.sub("", text).strip()
    # 剥 ``` 围栏(可能带语言标识)
    if text.startswith("```"):
        text = _FENCE_RE.sub("", text, count=1)
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    # 直接尝试整体解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 退化:找最后一个平衡括号块再解析
    blob = _find_last_balanced_object(text)
    if blob is None:
        raise ValueError(f"reasoner did not return JSON: {text[:200]}")
    return json.loads(blob)


def _safe_slug(value: str, fallback: str = "run") -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", value).strip("_")
    return cleaned[:40] or fallback


def _log(scope: str, message: str) -> None:
    """简易 stdout 日志,带时间戳,flush=True 让 Jupyter cell 实时显示。"""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{scope}] {message}", flush=True)


def _fmt_exc(e: BaseException) -> str:
    return f"{type(e).__name__}: {e}"


def _build_mapping_block(refs_with_roles: list[tuple[Path, str]]) -> str:
    """生成 photo-role mapping 文本,附加在图像编辑 prompt 末尾。

    GPT-Image-2 的 images.edit 接收多张图却不区分语义角色,需要明确告知每张图扮演
    的角色。本块**只做位置 → 角色名绑定**,角色的具体用途/约束完全由预写 prompt
    里的「参考图分工如下」段落定义(单一真理)。

    role 字符串必须使用预写 prompt 里出现的 exact 角色名(如「kigurumi头壳案例图」),
    避免引入与预写定义冲突的新描述。
    """
    if not refs_with_roles:
        return ""
    lines = [f"- 图 {i+1}:{role}" for i, (_, role) in enumerate(refs_with_roles[:16])]
    block = (
        "\n\n以下确认每张图的角色(请按此角色查阅上文「参考图分工如下」中的具体说明):\n"
        + "\n".join(lines)
    )
    # 预写「参考图分工如下」里的「不要复制」条款没覆盖店家成品照常带的水印/品牌 LOGO。
    # 这是 hoshino step3 把案例图水印复制到结果的真实 gap,这里补一句。
    if any("案例图" in role for _, role in refs_with_roles):
        block += "\n案例图中若包含水印、品牌 LOGO 或店家名称文字,严禁复制到结果。"
    return block


# 给 reasoner(评审 / 漂移检测 / 跨轮挑选 / 数据集视觉选)用的总则。
# 用户提供的 CHAR_REF_PATHS + EXPR_REF_PATH(下方图像块)是事实,CHAR_INFO 文本
# (下方『目标角色信息』段落)默认是约束/描述,不能用来推翻参考图;只有当 CHAR_INFO
# 出现「把参考图的 X 改成 Y」之类的显式修改指令时,才作为对参考图的覆盖目标。
_REASONER_REFS_VS_TEXT_PRINCIPLE = (
    "【核心原则:参考图权重 > 文字描述】\n"
    "用户提供的参考图(后文以图像块形式呈现:角色参考图 / 表情参考图 / Step N 选中头壳等)"
    "是事实来源,具有最高权重 —— 角色身份、发型轮廓、发色、五官、配色、装饰、表情等"
    "视觉信息一律以对应参考图为准。\n"
    "用户提供的『目标角色信息』文本描述默认仅作为补充约束 —— 用来标注参考图里那些"
    "值得保留的特征,不能用来推翻参考图。当文字描述与参考图视觉冲突时,以参考图为准。\n"
    "唯一例外:若『目标角色信息』里明确出现「把参考图的 X 改成 Y」「将参考图的 A 调整为 B」"
    "这类显式修改指令,才视为对参考图的覆盖目标,此时用文字为准。\n\n"
)


# --------------------------- Agent ---------------------------

class KigurumiAgent:
    def __init__(self, config: AgentConfig):
        self.cfg = config
        self.prompts: dict[int, StepPrompts] = load_all()
        self.image_client = OpenAI(api_key=config.image.api_key, base_url=config.image.base_url)
        self.reason_client = OpenAI(api_key=config.reason.api_key, base_url=config.reason.base_url)

    # ---- 对外入口 ----

    def run(
        self,
        char_ref_paths: Sequence[str | Path],
        char_info: str,
        expr_ref_path: str | Path,
        run_label: str | None = None,
    ) -> AgentResult:
        char_refs = [Path(p) for p in char_ref_paths]
        expr_ref = Path(expr_ref_path)
        for p in [*char_refs, expr_ref]:
            if not p.exists():
                raise FileNotFoundError(p)

        run_dir = self._init_run_dir(run_label or _safe_slug(char_info.splitlines()[0]))
        _log("agent", f"run start: run_dir={run_dir.name}, char_refs={len(char_refs)}, "
                      f"expr_ref={expr_ref.name}, image_model={self.cfg.image.model}, "
                      f"reason_model={self.cfg.reason.model}, max_refine={self.cfg.max_refine}")
        self._write_text(run_dir, "char_info.txt", char_info)
        self._copy_inputs(run_dir, char_refs, expr_ref)

        t_run = time.time()
        try:
            step1 = self._run_step1(char_refs, expr_ref, char_info, run_dir)
            assert step1.best is not None, "step1.best should be set by _run_refine_step"
            similar = self._select_similar(char_refs[0], char_info, run_dir)
            step2 = self._run_step2(step1.best, expr_ref, similar, char_info, run_dir)
            assert step2.best is not None, "step2.best should be set by _run_refine_step"
            step3 = self._run_step3(step2.best, similar, expr_ref, char_info, run_dir)
        except Exception as e:
            _log("agent", f"run FAILED after {time.time()-t_run:.1f}s: {_fmt_exc(e)}")
            raise

        result = AgentResult(run_dir=run_dir, step1=step1, step2=step2, step3=step3, similar=similar)
        (run_dir / "run.json").write_text(
            json.dumps(result.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _log("agent", f"run complete in {time.time()-t_run:.1f}s, run_dir={run_dir}")
        return result

    # ---- 阶段编排 ----

    def _run_step1(self, char_refs: list[Path], expr_ref: Path, char_info: str, run_dir: Path) -> StepRun:
        # 角色名严格对齐 prompts/step1-head-reference.md 中的「参考图分工如下」:
        #   1. 结构参考图  2. 表情参考图  3. 官方角色图
        # agent 输入只有 char_refs + expr_ref,把第 1 张 char 作「结构」,其余作「官方」。
        base_refs_with_roles: list[tuple[Path, str]] = []
        for i, p in enumerate(char_refs):
            base_refs_with_roles.append((p, "结构参考图" if i == 0 else "官方角色图"))
        base_refs_with_roles.append((expr_ref, "表情参考图"))
        return self._run_refine_step(
            step_id=1, base_refs_with_roles=base_refs_with_roles, expr_ref=expr_ref,
            char_info=char_info, run_dir=run_dir, output_name="step1_best.png",
        )

    def _run_step2(
        self, step1_best: Candidate, expr_ref: Path, similar: list[Path], char_info: str, run_dir: Path,
    ) -> StepRun:
        # 角色名严格对齐 prompts/step2-kigurumi-design.md 中的「参考图分工如下」:
        #   1. 角色头部四视图设定图  2. 目标表情参考图  3. kigurumi头壳案例图
        base_refs_with_roles: list[tuple[Path, str]] = [
            (step1_best.path, "角色头部四视图设定图"),
            (expr_ref, "目标表情参考图"),
        ]
        for p in similar:
            base_refs_with_roles.append((p, "kigurumi头壳案例图"))
        return self._run_refine_step(
            step_id=2, base_refs_with_roles=base_refs_with_roles, expr_ref=expr_ref,
            char_info=char_info, run_dir=run_dir, output_name="step2_best.png",
        )

    def _run_refine_step(
        self, *, step_id: int, base_refs_with_roles: list[tuple[Path, str]], expr_ref: Path,
        char_info: str, run_dir: Path, output_name: str,
    ) -> StepRun:
        """Step 1 / Step 2 共用的「通用 + 修正」流程。

        每轮 candidates 累积到 ``all_candidates`` 里。轮内的 verdict 只决定
        「下一轮以哪张为参考」以及「用哪个修正 prompt」。循环结束(accept
        或达到最大修正次数)后,跨所有轮做一次最终挑选 —— 对应 spec
        中「检查结束后从生成的图片对比,选择效果最好的图片」。
        """
        scope = f"step{step_id}"
        # _review / _final_pick 仍按旧签名收纯路径列表;_generate 走带角色版本
        base_refs: list[Path] = [r[0] for r in base_refs_with_roles]
        _log(scope, f"start: base_refs={len(base_refs)}, max_refine={self.cfg.max_refine}")
        t_step = time.time()

        sp = self.prompts[step_id]
        step = StepRun(step=step_id)
        refinement_keys = list(sp.refinements.keys())
        all_candidates: list[Candidate] = []

        _log(scope, "iter0 generate (key=general)")
        t = time.time()
        candidates = self._generate(
            step=step_id, iteration=0, prompt_key="general",
            prompt=sp.general, refs_with_roles=base_refs_with_roles, run_dir=run_dir,
        )
        _log(scope, f"iter0 generated {len(candidates)} candidates in {time.time()-t:.1f}s")
        all_candidates.extend(candidates)

        _log(scope, "iter0 review")
        t = time.time()
        verdict = self._review(
            step=step_id, candidates=candidates, refs=base_refs,
            char_info=char_info, expr_ref=expr_ref, refinement_keys=refinement_keys,
        )
        _log(scope, f"iter0 verdict={verdict['verdict']} best={verdict['best_index']} "
                    f"refine_key={verdict.get('refine_key')} ({time.time()-t:.1f}s) "
                    f"notes={verdict.get('notes')!r}")
        step.iterations.append({
            "prompt_key": "general",
            "candidates": [c.as_dict() for c in candidates],
            "verdict": verdict,
        })

        for iteration in range(1, self.cfg.max_refine + 1):
            if verdict["verdict"] == "accept":
                _log(scope, f"early-exit after iter{iteration-1}: verdict=accept")
                break
            best_so_far = candidates[verdict["best_index"]]
            raw_key = verdict.get("refine_key")
            initial_key: str
            if isinstance(raw_key, str) and raw_key in sp.refinements:
                initial_key = raw_key
            else:
                _log(scope, f"reasoner returned invalid refine_key={raw_key!r}, "
                            f"falling back to {refinement_keys[0]!r}")
                initial_key = refinement_keys[0]

            # 二次推理:让 reasoner 检查 refine_key + notes,在 reuse / switch / append / rewrite 四选一
            refine_key, refine_prompt, refine_mode = self._adjust_refine_prompt(
                initial_key=initial_key,
                notes=verdict.get("notes") or "",
                refinements=sp.refinements,
            )
            prompt_modified = refine_mode in ("append", "rewrite")

            # 修正轮:把当前最佳作为主参考,再带上原始参考(角色标注)保持上下文。
            # 角色标签简洁即可:refine 预写 prompt 不带「参考图分工如下」,
            # 主参考的语义靠 refine 文本本身(『请基于当前结果继续微调...』)说明。
            new_refs_with_roles: list[tuple[Path, str]] = [
                (best_so_far.path, f"当前最佳图(iter{iteration-1},本轮微调对象)"),
                *base_refs_with_roles,
            ]
            _log(scope, f"iter{iteration} generate (key={refine_key}, mode={refine_mode}, "
                        f"primary={best_so_far.path.name})")
            t = time.time()
            candidates = self._generate(
                step=step_id, iteration=iteration, prompt_key=refine_key,
                prompt=refine_prompt, refs_with_roles=new_refs_with_roles, run_dir=run_dir,
            )
            _log(scope, f"iter{iteration} generated {len(candidates)} candidates in {time.time()-t:.1f}s")
            all_candidates.extend(candidates)
            t = time.time()
            verdict = self._review(
                step=step_id, candidates=candidates, refs=base_refs,
                char_info=char_info, expr_ref=expr_ref, refinement_keys=refinement_keys,
            )
            _log(scope, f"iter{iteration} verdict={verdict['verdict']} best={verdict['best_index']} "
                        f"refine_key={verdict.get('refine_key')} ({time.time()-t:.1f}s) "
                        f"notes={verdict.get('notes')!r}")
            step.iterations.append({
                "prompt_key": refine_key,
                "initial_key": initial_key,
                "refine_mode": refine_mode,
                "prompt_modified": prompt_modified,
                "prompt_used": refine_prompt,
                "candidates": [c.as_dict() for c in candidates],
                "verdict": verdict,
            })

        _log(scope, f"final pick across {len(all_candidates)} candidates")
        t = time.time()
        step.best = self._final_pick(
            step=step_id, candidates=all_candidates, refs=base_refs,
            char_info=char_info, expr_ref=expr_ref,
        )
        _log(scope, f"final pick -> {step.best.path.name} "
                    f"(iter{step.best.iteration} key={step.best.prompt_key}) in {time.time()-t:.1f}s")
        self._save_best(step.best, run_dir, output_name)
        _log(scope, f"done in {time.time()-t_step:.1f}s, best={output_name}")
        return step

    def _run_step3(
        self, step2_best: Candidate, similar: list[Path], expr_ref: Path,
        char_info: str, run_dir: Path,
    ) -> StepRun:
        scope = "step3"
        _log(scope, f"start: refs=step2_best + {len(similar)} similar + expr_ref (no refine loop)")
        t_step = time.time()

        sp = self.prompts[3]
        # 角色名严格对齐 prompts/step3-product-view.md 中的「参考图分工如下」:
        #   1. kigurumi头壳设计图  2. 商品照案例图  3. 表情参考图
        refs_with_roles: list[tuple[Path, str]] = [
            (step2_best.path, "kigurumi头壳设计图"),
        ]
        for p in similar:
            refs_with_roles.append((p, "商品照案例图"))
        refs_with_roles.append((expr_ref, "表情参考图"))
        step = StepRun(step=3)
        _log(scope, "generate (key=four)")
        t = time.time()
        candidates = self._generate(
            step=3, iteration=0, prompt_key="four",
            prompt=sp.refinements.get("four", sp.general),
            refs_with_roles=refs_with_roles, run_dir=run_dir,
        )
        _log(scope, f"generated {len(candidates)} candidates in {time.time()-t:.1f}s")

        # P1: drift review —— 检查 step3 是否被商品照案例污染了 step2 选定的角色身份
        _log(scope, "drift review")
        t = time.time()
        drift = self._review_step3_drift(
            candidates=candidates, step2_best=step2_best,
            similar=similar, expr_ref=expr_ref, char_info=char_info,
        )
        _log(scope, f"drift review ({time.time()-t:.1f}s): best={drift['best_index']}, "
                    f"drift={drift['drift']}, fall_back={drift['fall_back_to_step2']}, "
                    f"notes={drift['notes']!r}")
        if drift["drift"]:
            _log(scope, "=" * 60)
            _log(scope, "⚠ DRIFT DETECTED — step3 may have been polluted by case photos:")
            _log(scope, f"   {drift['notes']}")
            if drift["fall_back_to_step2"]:
                _log(scope, "   reasoner suggests fall back to step2_best (severe drift)")
            _log(scope, "   inspect step2_best.png vs step3_best.png side by side")
            _log(scope, "=" * 60)

        step.iterations.append({
            "prompt_key": "four",
            "candidates": [c.as_dict() for c in candidates],
            "verdict": drift,
        })
        step.best = candidates[drift["best_index"]]
        self._save_best(step.best, run_dir, "step3_best.png")
        _log(scope, f"done in {time.time()-t_step:.1f}s, best=step3_best.png")
        return step

    def _review_step3_drift(
        self, *, candidates: list[Candidate], step2_best: Candidate,
        similar: list[Path], expr_ref: Path, char_info: str,
    ) -> dict:
        """Step 3 专用 review:检查商品照是否被案例图污染了 step2 选定的角色身份。

        返回 {"best_index", "drift", "fall_back_to_step2", "notes"}。
        失败时回退到 best_index=0、drift=False(不报警)。
        """
        system = _REASONER_REFS_VS_TEXT_PRINCIPLE + (
            "你是一位严格的艺术总监,负责检查 Step 3 商品照是否仍忠于 Step 2 选定的"
            "Kigurumi 头壳身份。只返回 JSON,不要其他文本。"
        )
        instructions = (
            "Step 3 目标:白底商品照风格的 kigurumi 头壳四面视图。\n\n"
            "基准:Step 2 选中的头壳(下方第一张图)是必须保留的角色身份依据 —— 发型轮廓、"
            "发色、眼睛(异色瞳/光环等装饰)、面壳表情、配饰位置都要忠于这张。\n"
            "商品照案例图(下方紧随)只用来教拍摄风格 —— 严禁复制其角色五官、发型、装饰或水印。\n\n"
            f"以下是 {len(candidates)} 张本轮 Step 3 候选图,编号 0..n-1。\n\n"
            "请按以下维度评估,挑出最佳并判断是否漂移:\n"
            "- [A] 角色身份是否仍像 Step 2 选定头壳?(发型/发色/眼睛/光环/装饰 全部对照)\n"
            "- [B] 是否被商品照案例污染?(发型变成案例的、装饰被复制、案例水印出现在结果里)\n"
            "- [C] 是否成为商品照风格?(白底、干净拍摄、材质质感)\n"
            "- [D] 四视图一致性\n\n"
            "返回 JSON:\n"
            "{\n"
            '  "best_index": <int>,                 // 在 0..n-1 范围内\n'
            '  "drift": <true|false>,               // [A] 失败或 [B] 出现污染时为 true\n'
            '  "fall_back_to_step2": <true|false>,  // 漂移严重到建议直接用 step2_best 兜底\n'
            '  "notes": "<具体定位问题, 中文>"\n'
            "}"
        )
        user_blocks: list[dict] = [{"type": "text", "text": instructions}]
        if char_info:
            user_blocks.append({"type": "text", "text": f"目标角色信息:\n{char_info}"})
        user_blocks.append({"type": "text", "text": "Step 2 选中头壳(角色身份基准,必须保留):"})
        user_blocks.append({"type": "image_url", "image_url": {"url": _to_data_url(step2_best.path)}})
        if similar:
            user_blocks.append({"type": "text", "text": "商品照案例图(仅风格参考,严禁复制角色):"})
            for p in similar:
                user_blocks.append({"type": "image_url", "image_url": {"url": _to_data_url(p)}})
        if expr_ref:
            user_blocks.append({"type": "text", "text": "目标表情参考:"})
            user_blocks.append({"type": "image_url", "image_url": {"url": _to_data_url(expr_ref)}})
        user_blocks.append({"type": "text", "text": f"Step 3 候选图(编号 0..{len(candidates)-1}):"})
        for c in candidates:
            user_blocks.append({"type": "image_url", "image_url": {"url": _to_data_url(c.path)}})

        try:
            data = self._chat_json(system=system, user_blocks=user_blocks)
        except Exception as e:
            _log("step3", f"drift review FAILED, treating as no-drift: {_fmt_exc(e)}")
            return {"best_index": 0, "drift": False, "fall_back_to_step2": False, "notes": ""}

        return {
            "best_index": self._coerce_index(data.get("best_index"), len(candidates), 0),
            "drift": bool(data.get("drift", False)),
            "fall_back_to_step2": bool(data.get("fall_back_to_step2", False)),
            "notes": data.get("notes", ""),
        }

    # ---- 复用既有 run 重跑 step3(用于隔离测试 P0+P1) ----

    def rerun_step3(
        self, source_run_dir: str | Path, label_suffix: str = "rerun-step3",
    ) -> StepRun:
        """复用既有 run 的 step2_best + similar + expr_ref + char_info,只重跑 Step 3。

        用于隔离测试 step3 改动,无需重新跑 step1 / step2。
        新结果落到全新的 run_dir 下,不污染原 run。
        """
        src = Path(source_run_dir)
        if not src.is_dir():
            raise NotADirectoryError(src)

        step2_best_path = src / "step2_best.png"
        if not step2_best_path.exists():
            raise FileNotFoundError(step2_best_path)

        similar_dir = src / "similar"
        similar = sorted(p for p in similar_dir.iterdir() if p.is_file()) if similar_dir.exists() else []

        inputs_dir = src / "inputs"
        expr_candidates = sorted(inputs_dir.glob("expression.*")) if inputs_dir.exists() else []
        if not expr_candidates:
            raise FileNotFoundError(f"no expression.* in {inputs_dir}")
        expr_ref = expr_candidates[0]

        char_info_path = src / "char_info.txt"
        char_info = char_info_path.read_text(encoding="utf-8") if char_info_path.exists() else ""

        new_run_dir = self._init_run_dir(f"{src.name}_{label_suffix}")
        _log("agent", f"rerun_step3 start: source={src.name}, new_run_dir={new_run_dir.name}")
        self._write_text(new_run_dir, "char_info.txt", char_info)
        self._write_text(new_run_dir, "source.txt", str(src))

        # 用合成的 Candidate 包一下 step2_best,让 _run_step3 的签名兼容
        fake_step2 = Candidate(
            path=step2_best_path, step=2, iteration=0,
            prompt_key="general", index=0,
        )
        step3 = self._run_step3(fake_step2, similar, expr_ref, char_info, new_run_dir)
        assert step3.best is not None

        audit = {
            "source_run_dir": str(src),
            "step2_best": str(step2_best_path),
            "similar": [str(p) for p in similar],
            "expr_ref": str(expr_ref),
            "step3": step3.as_dict(),
        }
        (new_run_dir / "rerun.json").write_text(
            json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _log("agent", f"rerun_step3 complete, run_dir={new_run_dir}")
        return step3

    # ---- 图像生成 ----

    def _generate(
        self, *, step: int, iteration: int, prompt_key: str, prompt: str,
        refs_with_roles: list[tuple[Path, str]], run_dir: Path,
    ) -> list[Candidate]:
        # 末尾追加 photo-role mapping,告诉模型不同图的角色(主参考 / 表情 / 案例),
        # 避免案例图的角色身份/装饰/水印被复制到结果里。
        final_prompt = prompt + _build_mapping_block(refs_with_roles)
        refs = [r[0] for r in refs_with_roles[:16]]
        opened: list = []
        try:
            for p in refs:
                opened.append(open(p, "rb"))
            # 兼容不同版本 openai SDK:旧版的 images.edit 可能没有把 size/quality
            # 暴露成命名参数。SDK 接受的走命名参数,其余走 extra_body 透传给上游 API。
            direct: dict[str, Any] = {
                "model": self.cfg.image.model,
                "prompt": final_prompt,
                "image": opened,
                "n": self.cfg.image.n,
            }
            extra_body: dict[str, Any] = {}
            for key, value in (
                ("size", self.cfg.image.size or "auto"),
                ("quality", self.cfg.image.quality or "auto"),
            ):
                if key in _EDIT_PARAMS:
                    direct[key] = value
                else:
                    extra_body[key] = value
            if extra_body:
                direct["extra_body"] = extra_body
            response = self.image_client.images.edit(**direct)
        finally:
            for fh in opened:
                try:
                    fh.close()
                except Exception:
                    pass

        step_dir = run_dir / f"step{step}"
        step_dir.mkdir(exist_ok=True)
        candidates: list[Candidate] = []
        items = response.data or []
        for index, item in enumerate(items):
            b64 = item.b64_json
            if b64 is not None:
                data = base64.b64decode(b64)
            else:
                # 兜底:有些端点返回的是 url 而不是 base64
                url = getattr(item, "url", None)
                if not url:
                    raise RuntimeError("image response had neither b64_json nor url")
                import urllib.request
                data = urllib.request.urlopen(url).read()
            filename = f"iter{iteration:02d}_{prompt_key}_{index}.png"
            path = step_dir / filename
            path.write_bytes(data)
            candidates.append(Candidate(path=path, step=step, iteration=iteration, prompt_key=prompt_key, index=index))
        return candidates

    # ---- 评审 / 修正 ----

    def _review(
        self, *, step: int, candidates: list[Candidate], refs: list[Path],
        char_info: str, expr_ref: Path, refinement_keys: list[str],
    ) -> dict:
        """让 reasoner 在本轮候选里挑最佳,并决定 accept 还是 refine。"""
        default_index = 0 if len(candidates) == 1 else -1

        system = _REASONER_REFS_VS_TEXT_PRINCIPLE + (
            "你是一位严格的艺术总监,负责审查 Kigurumi 角色参考图渲染结果。"
            "对照目标角色参考图和目标表情,挑出当前最佳候选,并判断是否需要单项修正。"
            "只返回一个 JSON 对象,不要包含任何额外文本。"
        )
        instructions = self._review_instructions(step, refinement_keys, len(candidates))
        user_blocks: list[dict] = [
            {"type": "text", "text": instructions},
            {"type": "text", "text": f"目标角色信息:\n{char_info}"},
            {"type": "text", "text": "以下是目标角色参考图:"},
        ]
        for p in refs:
            user_blocks.append({"type": "image_url", "image_url": {"url": _to_data_url(p)}})
        user_blocks.append({"type": "text", "text": "目标表情参考图:"})
        user_blocks.append({"type": "image_url", "image_url": {"url": _to_data_url(expr_ref)}})
        user_blocks.append({"type": "text", "text": "以下为本轮候选图,按编号 0..n-1 排列:"})
        for c in candidates:
            user_blocks.append({"type": "image_url", "image_url": {"url": _to_data_url(c.path)}})

        verdict_raw = self._chat_json(system=system, user_blocks=user_blocks)
        verdict_raw["best_index"] = self._coerce_index(
            verdict_raw.get("best_index"), len(candidates), default_index,
        )
        if verdict_raw.get("verdict") not in ("accept", "refine"):
            verdict_raw["verdict"] = "accept"
        if verdict_raw["verdict"] == "refine" and verdict_raw.get("refine_key") not in refinement_keys:
            verdict_raw["refine_key"] = refinement_keys[0] if refinement_keys else None
        return verdict_raw

    @staticmethod
    def _coerce_index(value, n: int, default: int) -> int:
        try:
            i = int(value)
        except (TypeError, ValueError):
            return max(0, default)
        if 0 <= i < n:
            return i
        return max(0, min(n - 1, default if default >= 0 else 0))

    @staticmethod
    def _review_instructions(step: int, refinement_keys: list[str], n_candidates: int) -> str:
        if step == 1:
            target = (
                "Step 1 目标:白底干净的角色去遮挡头部四视图(正面 / 左前45度 / 左侧面 / 背面),"
                "保留必要的小发饰,不要 kigurumi 头壳,不要真人/3D/手办风格。"
            )
            step_specific = (
                "[F] Step 1 专项\n"
                "  - 遮挡物(兜帽/帽子/面罩/口罩等)是否清除?\n"
                "  - 必要的小发饰是否保留(发卡、缎带、角饰等)?\n"
                "  - 是否仍是动漫设定图风格,而非 kigurumi 头壳?\n"
            )
        elif step == 2:
            target = (
                "Step 2 目标:白底 animegao kigurumi 头壳四视图(正面 / 左前45度 / 左侧面 / 背面)——"
                "硬质平滑面壳、固定表情、真实假发、有眼眶结构的大眼睛,适合实体制作。"
            )
            step_specific = (
                "[F] Step 2 专项(animegao 头壳特征)\n"
                "  - 头壳感:面壳是否硬质平滑、有实体感?还是普通插画脸?\n"
                "  - 眼眶结构:眼眶厚度、眼线、睫毛是否符合实体头壳?\n"
                "  - 假发处理:发丝质感是否像真实假发,而非插画头发?\n"
                "  - 面壳立体度:鼻子是否弱化、嘴巴是否简化、整体不过度 3D?\n"
                "  - 侧面厚度:左侧面/背面是否能看到头壳厚度与后脑体积?\n"
            )
        else:
            target = "Step 3 目标:白底商品照风格的 kigurumi 头壳四面视图,干净拍摄、连续旋转。"
            step_specific = (
                "[F] Step 3 专项(商品照风格)\n"
                "  - 白底拍摄质量、商品图排版是否干净?\n"
                "  - 头壳材质、假发纤维质感是否到位?\n"
                "  - 是否仍然是 kigurumi 头壳,而非真人 cosplay / 普通动漫头像?\n"
            )

        return (
            f"{target}\n\n"
            f"本轮共 {n_candidates} 张候选图。请按以下细粒度清单评估,挑出最契合的那张。\n\n"
            "[A] 角色身份还原(必查)\n"
            "  - 发型轮廓、发色是否准确?\n"
            "  - 耳朵位置、虹膜颜色是否对得上?\n"
            "  - 整体气质是否还原目标角色?\n"
            "[B] 目标表情(必查,以表情参考图为准)\n"
            "  - 眉毛角度、眼神方向\n"
            "  - 上眼睑 / 下眼睑形状\n"
            "  - 嘴形与整体情绪(不要自动微笑)\n"
            "[C] 脸型\n"
            "  - 是否圆润、幼态、短下巴?\n"
            "  - 脸颊饱满度、下颌线柔和度\n"
            "[D] 五官细节\n"
            "  - 鼻子立体度(过强是问题)\n"
            "  - 嘴形、是否对称\n"
            "  - 眼距与眉眼关系\n"
            "[E] 妆面与皮肤质感\n"
            "  - 唇彩、口红是否过重/颜色异常?\n"
            "  - 腮红、眼影、眼线是否过度?\n"
            "  - 皮肤是否出现真人质感、毛孔、过度高光?\n"
            f"{step_specific}"
            "[G] 四视图一致性\n"
            "  - 四个视角是否同一个角色、同一发型、同一表情?\n"
            "[H] 风格底线\n"
            "  - 不能是真人 / cosplay 妆面 / 手办 / BJD / 写实 3D 渲染\n\n"
            "评估后判断:\n"
            "- verdict = 'accept':最佳候选整体已经够好,可以进入下一阶段;\n"
            "- verdict = 'refine':需要选一个 refine_key 做单项定向修正。\n"
            f"可选的 refine_key 取值:{refinement_keys}\n"
            "notes 字段要尽量精准定位问题在以上哪一项(例如 \"[E] 唇彩偏红、[F] 头壳眼眶过薄\"),"
            "便于下一步精修。\n\n"
            "只返回 JSON,结构为:"
            '{"best_index": <int>, "verdict": "accept"|"refine", '
            '"refine_key": "<上述列表之一或 null>", "notes": "<具体定位到清单字母的简短中文>"}'
        )

    # rewrite 模式下,新 prompt 必须包含下列任意一种「保持不变」类锚点,
    # 防止 reasoner 重写时不小心丢掉所有约束、放飞图像模型重新画
    _REWRITE_SAFETY_PHRASES = ("保持不变", "不要重新设计", "不要改变", "保留", "保持")

    def _adjust_refine_prompt(
        self, *, initial_key: str, notes: str, refinements: dict[str, str],
    ) -> tuple[str, str, str]:
        """每次 refine 前的二次推理:决定最终 refine_key + 是否调整预写 prompt。

        四种处理模式(给 reasoner 的优先级,从高到低):
        - 'reuse'   备注已被选定 refine_key 的预写 prompt 充分覆盖 -> 直接复用
        - 'switch'  另一个预写 refine_key 更贴切 -> 切换 key,使用其原 prompt
        - 'append'  备注比预写 prompt 更细致(角度/位置/程度) -> 在原文末尾追加 1-2 行
        - 'rewrite' 备注涉及预写 prompts 完全没覆盖的维度(妆面/唇彩/材质等),且前三种都
                    不合适 -> 按预写格式重写完整 prompt,final_key 用最接近的标签

        返回 (final_key, final_prompt, mode)。失败/异常时回退到 ('reuse', ...)。
        """
        original_prompt = refinements[initial_key]
        # 备注为空时跳过二次推理,直接复用预写 prompt
        if not notes.strip():
            return initial_key, original_prompt, "reuse"

        scope = "refine-adjust"
        catalog = "\n\n".join(f"=== key={k} ===\n{prompt}" for k, prompt in refinements.items())
        system = (
            "你是 prompt 调整器,负责为图像编辑流水线选定/调整 refine prompt,使其精准匹配"
            "上一轮评审的备注。\n\n"
            "四种处理模式(从高到低优先级,选最低优先级的那个):\n\n"
            "A. mode='reuse'(直接复用):备注问题已被选定 refine_key 的预写 prompt 充分覆盖。\n"
            "   final_key=initial_key,final_prompt=原 prompt(完全不变)。\n\n"
            "B. mode='switch'(切换 key):另一个预写 refine_key 的 prompt 更贴切备注问题。\n"
            "   final_key=新 key,final_prompt=新 key 的原 prompt(完全不变)。\n\n"
            "C. mode='append'(追加微调):备注比预写 prompt 更细致(具体角度/位置/程度),但维度仍在\n"
            "   预写 prompt 覆盖范围内。final_key=initial_key,final_prompt=原 prompt + 末尾追加\n"
            "   1-2 行精确指令。要求:\n"
            "   - 不能删除原文任何字句;\n"
            "   - 不能修改/移除『保持不变』类约束;\n"
            "   - 追加内容必须短(1-2 行),语气与原文保持一致(原文是描述式就用描述式,原文是\n"
            "     祈使式就用祈使式)。\n\n"
            "D. mode='rewrite'(完全重写,慎用):备注涉及妆面/唇彩/腮红/皮肤质感/材质/装饰物等\n"
            "   预写 prompts 完全没有覆盖的维度,且 A/B/C 都不合适。final_key=最接近的 initial_key\n"
            "   (仅作审计标签),final_prompt=按下列格式重新撰写的完整 prompt:\n"
            "   - 开头:『请基于当前结果继续微调,不要重新设计角色。』\n"
            "   - 列出本次要修正的具体点(对应备注),用显式祈使句式(『把 X 改为 Y』『将 A 调整为 B』)\n"
            "     比『需要 X』『应该 Y』更稳。\n"
            "   - 必须包含至少一处『保持不变』『不要改变』『保留』类的保护性约束(保护发型结构、\n"
            "     四视图排版、角色身份等不被破坏)\n"
            "   - 结尾:『输出仍然是同一个 [当前图类型] 设计图。』\n"
            "   - 长度不超过 600 字\n\n"
            "只返回一个 JSON 对象,不要其他文本。"
        )
        user_text = (
            f"上一轮评审选定的 refine_key:{initial_key}\n"
            f"评审备注:{notes}\n\n"
            f"可选预写 refine prompts(reuse/switch/append 只能在下列 key 中挑):\n{catalog}\n\n"
            '只返回 JSON:{"mode": "reuse"|"switch"|"append"|"rewrite", '
            '"final_key": "<key>", "final_prompt": "<完整文本>", "reason": "<简短中文说明>"}'
        )
        try:
            data = self._chat_json(
                system=system,
                user_blocks=[{"type": "text", "text": user_text}],
            )
        except Exception as e:
            _log(scope, f"FALLBACK to original (key={initial_key}, mode=reuse): {_fmt_exc(e)}")
            return initial_key, original_prompt, "reuse"

        mode = data.get("mode")
        if mode not in ("reuse", "switch", "append", "rewrite"):
            _log(scope, f"invalid mode={mode!r}, treating as reuse")
            mode = "reuse"

        final_key = data.get("final_key")
        if final_key not in refinements:
            _log(scope, f"invalid final_key={final_key!r}, keeping initial_key={initial_key}")
            final_key = initial_key

        final_prompt = data.get("final_prompt") or refinements[final_key]
        base_prompt = refinements[final_key]

        # 按 mode 分别做防御性校验:
        if mode == "reuse":
            # reuse 模式必须等于原 prompt,否则强制还原
            if final_prompt.strip() != base_prompt.strip():
                _log(scope, "reuse mode but text differs from base — forcing original")
                final_prompt = base_prompt
        elif mode == "switch":
            # switch 模式必须等于新 key 的原 prompt
            if final_prompt.strip() != base_prompt.strip():
                _log(scope, "switch mode but text differs from new key's base — forcing new key base")
                final_prompt = base_prompt
        elif mode == "append":
            # append 模式必须完整包含原文(否则就是非法删除)
            if base_prompt not in final_prompt:
                _log(scope, "append mode but base prompt not preserved — reverting to base")
                final_prompt = base_prompt
                mode = "reuse"
        elif mode == "rewrite":
            # rewrite 必须保留至少一处「保持不变」类的保护性约束
            if not any(p in final_prompt for p in self._REWRITE_SAFETY_PHRASES):
                _log(scope, "rewrite mode missing safety constraint — reverting to base")
                final_prompt = base_prompt
                mode = "reuse"
            elif len(final_prompt) > 1500:
                _log(scope, f"rewrite prompt too long ({len(final_prompt)} chars) — reverting to base")
                final_prompt = base_prompt
                mode = "reuse"

        _log(scope, f"mode={mode}, key={initial_key}->{final_key}, "
                    f"reason={data.get('reason')!r}")
        return final_key, final_prompt, mode

    def _final_pick(
        self, *, step: int, candidates: list[Candidate], refs: list[Path],
        char_info: str, expr_ref: Path,
    ) -> Candidate:
        """全部迭代结束后,跨所有候选做最终选择。

        对应 spec 中「检查结束后从生成的图片对比,选择效果最好的图片」。
        """
        if len(candidates) == 1:
            return candidates[0]

        if step == 1:
            target = "Step 1 —— 白底角色去遮挡头部四视图。"
        elif step == 2:
            target = "Step 2 —— 白底 animegao kigurumi 头壳四视图。"
        else:
            target = "Step 3 —— 白底商品照风格的 kigurumi 头壳四面视图。"

        system = _REASONER_REFS_VS_TEXT_PRINCIPLE + (
            "你是一位严格的艺术总监,需要做最终选择。只返回 JSON 对象,不要其他文本。"
        )
        blocks: list[dict] = [
            {"type": "text", "text": (
                f"{target}\n\n"
                f"以下共 {len(candidates)} 张候选图来自多轮迭代。请综合:角色身份还原度、"
                "目标表情吻合度、四视图结构一致性、kigurumi 风格适配度,挑出最好的一张。"
                '只返回 JSON:{"best_index": <int>, "notes": "<简短中文理由>"}'
            )},
        ]
        if char_info:
            blocks.append({"type": "text", "text": f"目标角色信息:\n{char_info}"})
        if refs:
            blocks.append({"type": "text", "text": "参考图(目标角色 + 上下文):"})
            for p in refs:
                blocks.append({"type": "image_url", "image_url": {"url": _to_data_url(p)}})
        if expr_ref:
            blocks.append({"type": "text", "text": "目标表情参考图:"})
            blocks.append({"type": "image_url", "image_url": {"url": _to_data_url(expr_ref)}})
        blocks.append({"type": "text", "text": f"候选图(编号 0..{len(candidates)-1}):"})
        for i, c in enumerate(candidates):
            blocks.append({"type": "text", "text": f"index {i}: step{c.step} iter{c.iteration} key={c.prompt_key}"})
            blocks.append({"type": "image_url", "image_url": {"url": _to_data_url(c.path)}})
        try:
            data = self._chat_json(system=system, user_blocks=blocks)
            idx = self._coerce_index(data.get("best_index"), len(candidates), 0)
            return candidates[idx]
        except Exception as e:
            _log(f"step{step}", f"final-pick FALLBACK (last candidate): {_fmt_exc(e)}")
            return candidates[-1]

    # ---- 店家成品库相似度选择 ----

    def _select_similar(self, primary_ref: Path, char_info: str, run_dir: Path) -> list[Path]:
        scope = "similar"
        _log(scope, f"start: scanning {DATASET_DIR}")
        t_step = time.time()

        folders = sorted(p for p in DATASET_DIR.iterdir() if p.is_dir())
        if not folders or self.cfg.similar_top_k <= 0:
            _log(scope, f"skip: folders={len(folders)}, similar_top_k={self.cfg.similar_top_k}")
            return []

        # 阶段 A:仅看目录名,先用文本预筛收敛到 8 个候选
        names = [f.name for f in folders]
        _log(scope, f"text-prefilter: {len(names)} folders -> top {min(8, len(names))}")
        t = time.time()
        pre_pick = self._text_prefilter(char_info=char_info, names=names, top_n=min(8, len(names)))
        _log(scope, f"text-prefilter picks ({time.time()-t:.1f}s): {pre_pick}")
        shortlisted = [DATASET_DIR / n for n in pre_pick if (DATASET_DIR / n).is_dir()]
        if not shortlisted:
            _log(scope, "text-prefilter returned nothing, falling back to first 8 folders")
            shortlisted = folders[: min(8, len(folders))]

        # 阶段 B:把每个候选目录里的第一张图喂给视觉模型,挑出最终 [0, k] 张
        thumbs = [(folder, self._first_image(folder)) for folder in shortlisted]
        thumbs = [(folder, img) for folder, img in thumbs if img is not None]
        if not thumbs:
            _log(scope, "no thumbnails found in shortlisted folders, returning []")
            return []
        _log(scope, f"vision-pick: {len(thumbs)} thumbs -> up to {self.cfg.similar_top_k}")
        t = time.time()
        final = self._vision_pick(
            primary_ref=primary_ref, char_info=char_info, thumbs=thumbs, k=self.cfg.similar_top_k,
        )
        _log(scope, f"vision-pick picks ({time.time()-t:.1f}s): {[f.name for f in final]}")

        # 把选中的成品图拷贝到 run_dir/similar/ 下,后续 Step 2 / Step 3 直接引用
        sim_dir = run_dir / "similar"
        sim_dir.mkdir(exist_ok=True)
        out: list[Path] = []
        for folder in final:
            src = self._first_image(folder)
            if src is None:
                continue
            dst = sim_dir / f"{folder.name}{src.suffix}"
            shutil.copy2(src, dst)
            out.append(dst)
        _log(scope, f"done in {time.time()-t_step:.1f}s, copied {len(out)} into similar/")
        return out

    def _text_prefilter(self, *, char_info: str, names: list[str], top_n: int) -> list[str]:
        system = (
            "你需要根据店家成品库的目录名,为目标角色挑选最相似的若干条目。"
            "只返回 JSON 对象,不要其他文本。"
        )
        prompt = (
            f"目标角色信息:\n{char_info}\n\n"
            "店家成品库目录名(格式:作品-角色-版本):\n" + "\n".join(names) + "\n\n"
            f"请从中选出最多 {top_n} 个目录名,优先级:同作品 > 同风格 > 名称中可见的相似线索。"
            '只返回 JSON:{"picks": ["<完全相同的目录名>", ...]}'
        )
        try:
            data = self._chat_json(system=system, user_blocks=[{"type": "text", "text": prompt}])
            picks = data.get("picks", [])
            valid = [n for n in picks if n in names]
            return valid[:top_n]
        except Exception as e:
            _log("similar", f"text-prefilter FALLBACK (using first {top_n} names): {_fmt_exc(e)}")
            return names[:top_n]

    def _vision_pick(
        self, *, primary_ref: Path, char_info: str, thumbs: list[tuple[Path, Path]], k: int,
    ) -> list[Path]:
        system = _REASONER_REFS_VS_TEXT_PRINCIPLE + (
            "你是艺术总监,从店家成品里挑出最适合作为本次 Kigurumi 设计参考的若干张。"
            "只返回 JSON,不要其他文本。"
        )
        blocks: list[dict] = [
            {"type": "text", "text": (
                f"目标角色信息:\n{char_info}\n\n"
                f"下面依次是:目标角色参考图,然后是 {len(thumbs)} 张店家成品(编号 0..n-1,附目录名)。"
                f"请选出 0 到 {k} 张,要求其成品风格能为本次设计提供有效参考。"
                "优先匹配:发色、脸型、眼睛风格、整体气质。"
                '只返回 JSON:{"picks": [<int>...], "notes": "<简短中文理由>"}'
            )},
            {"type": "text", "text": "目标参考图:"},
            {"type": "image_url", "image_url": {"url": _to_data_url(primary_ref)}},
        ]
        for i, (folder, img) in enumerate(thumbs):
            blocks.append({"type": "text", "text": f"候选 {i}:{folder.name}"})
            blocks.append({"type": "image_url", "image_url": {"url": _to_data_url(img)}})
        try:
            data = self._chat_json(system=system, user_blocks=blocks)
            raw = data.get("picks", []) or []
            picks: list[Path] = []
            for v in raw:
                try:
                    idx = int(v)
                except (TypeError, ValueError):
                    continue
                if 0 <= idx < len(thumbs) and thumbs[idx][0] not in picks:
                    picks.append(thumbs[idx][0])
                if len(picks) >= k:
                    break
            return picks
        except Exception as e:
            _log("similar", f"vision-pick FALLBACK (using first {k} thumbs): {_fmt_exc(e)}")
            return [folder for folder, _ in thumbs[: max(0, k)]]

    @staticmethod
    def _first_image(folder: Path) -> Path | None:
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            for p in sorted(folder.glob(f"*{ext}")):
                return p
        return None

    # ---- 对话辅助 ----

    def _chat_json(self, *, system: str, user_blocks: list[dict]) -> dict:
        last_err: Exception | None = None
        for attempt in range(2):
            try:
                resp = self.reason_client.chat.completions.create(
                    model=self.cfg.reason.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_blocks},
                    ],
                    extra_body={"enable_thinking": True},
                    temperature=0.2,
                )
                text = resp.choices[0].message.content or ""
                return _extract_json(text)
            except Exception as e:
                last_err = e
                _log("reason", f"attempt {attempt+1}/2 failed: {_fmt_exc(e)}")
                time.sleep(1 + attempt)
        raise RuntimeError(f"reasoner JSON call failed: {last_err}")

    # ---- 运行目录与落盘 ----

    @staticmethod
    def _init_run_dir(label: str) -> Path:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = OUTPUT_DIR / f"{stamp}_{_safe_slug(label)}"
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    @staticmethod
    def _write_text(run_dir: Path, name: str, content: str) -> None:
        (run_dir / name).write_text(content, encoding="utf-8")

    @staticmethod
    def _copy_inputs(run_dir: Path, char_refs: Iterable[Path], expr_ref: Path) -> None:
        in_dir = run_dir / "inputs"
        in_dir.mkdir(exist_ok=True)
        for i, p in enumerate(char_refs):
            shutil.copy2(p, in_dir / f"char_{i:02d}{p.suffix}")
        shutil.copy2(expr_ref, in_dir / f"expression{expr_ref.suffix}")

    @staticmethod
    def _save_best(candidate: Candidate, run_dir: Path, name: str) -> None:
        shutil.copy2(candidate.path, run_dir / name)
