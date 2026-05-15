"""KigurumiAgent: 3-step pipeline that turns a character reference into
multi-view kigurumi product previews.

Pipeline:
1. Step 1 - de-occlusion head turnaround (GPT-Image-2 image edit + Qwen3.5 review/refine).
2. Pick 0-2 similar finished shop products from ../dataset/* (Qwen text-prefilter + vision pick).
3. Step 2 - kigurumi head shell turnaround (with step-1 best + expression ref + similar).
4. Step 3 - product-photo style 4-view (no refinement loop per spec).

The agent saves every candidate image and a `run.json` audit trail under
notebook/outputs/<run-id>/ so the user can inspect each refinement decision.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import re
import shutil
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from openai import OpenAI

from config import AgentConfig, DATASET_DIR, OUTPUT_DIR
from prompts import StepPrompts, load_all


# --------------------------- data classes ---------------------------

@dataclass
class Candidate:
    """One generated image kept on disk."""
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


# --------------------------- helpers ---------------------------

def _to_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> dict:
    """Tolerate Qwen wrapping JSON in prose or ``` fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[:-3]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_RE.search(text)
        if not match:
            raise ValueError(f"reasoner did not return JSON: {text[:200]}")
        return json.loads(match.group(0))


def _safe_slug(value: str, fallback: str = "run") -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", value).strip("_")
    return cleaned[:40] or fallback


# --------------------------- agent ---------------------------

class KigurumiAgent:
    def __init__(self, config: AgentConfig):
        self.cfg = config
        self.prompts: dict[int, StepPrompts] = load_all()
        self.image_client = OpenAI(api_key=config.image.api_key, base_url=config.image.base_url)
        self.reason_client = OpenAI(api_key=config.reason.api_key, base_url=config.reason.base_url)

    # ---- public entry point ----

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
        self._log(run_dir, "char_info.txt", char_info)
        self._copy_inputs(run_dir, char_refs, expr_ref)

        step1 = self._run_step1(char_refs, expr_ref, char_info, run_dir)
        similar = self._select_similar(char_refs[0], char_info, run_dir)
        step2 = self._run_step2(step1.best, expr_ref, similar, char_info, run_dir)
        step3 = self._run_step3(step2.best, similar, expr_ref, run_dir)

        result = AgentResult(run_dir=run_dir, step1=step1, step2=step2, step3=step3, similar=similar)
        (run_dir / "run.json").write_text(
            json.dumps(result.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return result

    # ---- step orchestration ----

    def _run_step1(self, char_refs: list[Path], expr_ref: Path, char_info: str, run_dir: Path) -> StepRun:
        return self._run_refine_step(
            step_id=1, base_refs=[*char_refs, expr_ref], expr_ref=expr_ref,
            char_info=char_info, run_dir=run_dir, output_name="step1_best.png",
        )

    def _run_step2(
        self, step1_best: Candidate, expr_ref: Path, similar: list[Path], char_info: str, run_dir: Path,
    ) -> StepRun:
        return self._run_refine_step(
            step_id=2, base_refs=[step1_best.path, expr_ref, *similar], expr_ref=expr_ref,
            char_info=char_info, run_dir=run_dir, output_name="step2_best.png",
        )

    def _run_refine_step(
        self, *, step_id: int, base_refs: list[Path], expr_ref: Path,
        char_info: str, run_dir: Path, output_name: str,
    ) -> StepRun:
        """Shared general+refine flow for steps 1 and 2.

        Each iteration's candidates are accumulated into ``all_candidates``; the
        intra-loop verdict only chooses which "best so far" feeds the next
        refinement. After the loop ends (accept or max refinements reached) a
        final pick runs across every candidate ever generated, matching the
        spec: "检查结束后从生成的图片对比，选择效果最好的图片".
        """
        sp = self.prompts[step_id]
        step = StepRun(step=step_id)
        refinement_keys = list(sp.refinements.keys())
        all_candidates: list[Candidate] = []

        candidates = self._generate(
            step=step_id, iteration=0, prompt_key="general",
            prompt=sp.general, refs=base_refs, run_dir=run_dir,
        )
        all_candidates.extend(candidates)
        verdict = self._review(
            step=step_id, candidates=candidates, refs=base_refs,
            char_info=char_info, expr_ref=expr_ref, refinement_keys=refinement_keys,
        )
        step.iterations.append({
            "prompt_key": "general",
            "candidates": [c.as_dict() for c in candidates],
            "verdict": verdict,
        })

        for iteration in range(1, self.cfg.max_refine + 1):
            if verdict["verdict"] == "accept":
                break
            best_so_far = candidates[verdict["best_index"]]
            refine_key = verdict.get("refine_key")
            if refine_key not in sp.refinements:
                refine_key = refinement_keys[0]
            refine_prompt = sp.refinements[refine_key]
            new_refs = [best_so_far.path, *base_refs]
            candidates = self._generate(
                step=step_id, iteration=iteration, prompt_key=refine_key,
                prompt=refine_prompt, refs=new_refs, run_dir=run_dir,
            )
            all_candidates.extend(candidates)
            verdict = self._review(
                step=step_id, candidates=candidates, refs=base_refs,
                char_info=char_info, expr_ref=expr_ref, refinement_keys=refinement_keys,
            )
            step.iterations.append({
                "prompt_key": refine_key,
                "candidates": [c.as_dict() for c in candidates],
                "verdict": verdict,
            })

        step.best = self._final_pick(
            step=step_id, candidates=all_candidates, refs=base_refs,
            char_info=char_info, expr_ref=expr_ref,
        )
        self._save_best(step.best, run_dir, output_name)
        return step

    def _run_step3(
        self, step2_best: Candidate, similar: list[Path], expr_ref: Path, run_dir: Path,
    ) -> StepRun:
        sp = self.prompts[3]
        refs = [step2_best.path, *similar, expr_ref]
        step = StepRun(step=3)
        candidates = self._generate(
            step=3, iteration=0, prompt_key="four",
            prompt=sp.refinements.get("four", sp.general), refs=refs, run_dir=run_dir,
        )
        step.iterations.append({"prompt_key": "four", "candidates": [c.as_dict() for c in candidates]})
        # No refine loop per spec; just pick best across candidates.
        step.best = (
            candidates[0]
            if len(candidates) == 1
            else self._final_pick(step=3, candidates=candidates, refs=refs, char_info="", expr_ref=expr_ref)
        )
        self._save_best(step.best, run_dir, "step3_best.png")
        return step

    # ---- image generation ----

    def _generate(
        self, *, step: int, iteration: int, prompt_key: str, prompt: str,
        refs: list[Path], run_dir: Path,
    ) -> list[Candidate]:
        opened = [open(p, "rb") for p in refs[:16]]
        try:
            kwargs = dict(
                model=self.cfg.image.model,
                prompt=prompt,
                image=opened,
                n=self.cfg.image.n,
            )
            if self.cfg.image.size and self.cfg.image.size != "auto":
                kwargs["size"] = self.cfg.image.size
            if self.cfg.image.quality and self.cfg.image.quality != "auto":
                kwargs["quality"] = self.cfg.image.quality
            response = self.image_client.images.edit(**kwargs)
        finally:
            for fh in opened:
                fh.close()

        step_dir = run_dir / f"step{step}"
        step_dir.mkdir(exist_ok=True)
        candidates: list[Candidate] = []
        for index, item in enumerate(response.data):
            b64 = item.b64_json
            if b64 is None:
                # url variant fallback
                if getattr(item, "url", None):
                    import urllib.request
                    data = urllib.request.urlopen(item.url).read()
                else:
                    raise RuntimeError("image response had neither b64_json nor url")
            else:
                data = base64.b64decode(b64)
            filename = f"iter{iteration:02d}_{prompt_key}_{index}.png"
            path = step_dir / filename
            path.write_bytes(data)
            candidates.append(Candidate(path=path, step=step, iteration=iteration, prompt_key=prompt_key, index=index))
        return candidates

    # ---- review / refinement ----

    def _review(
        self, *, step: int, candidates: list[Candidate], refs: list[Path],
        char_info: str, expr_ref: Path, refinement_keys: list[str],
    ) -> dict:
        """Ask the reasoner to pick the best candidate and decide refine vs accept."""
        if len(candidates) == 1:
            best_index = 0
        else:
            best_index = -1

        system = (
            "You are a strict art director reviewing kigurumi reference renders. "
            "Compare the candidate images against the target character references "
            "and target expression. Respond with a single JSON object only."
        )
        instructions = self._review_instructions(step, refinement_keys, len(candidates))
        user_blocks: list[dict] = [
            {"type": "text", "text": instructions},
            {"type": "text", "text": f"Target character info:\n{char_info}"},
            {"type": "text", "text": "Target character references follow:"},
        ]
        for p in refs:
            user_blocks.append({"type": "image_url", "image_url": {"url": _to_data_url(p)}})
        user_blocks.append({"type": "text", "text": "Target expression reference:"})
        user_blocks.append({"type": "image_url", "image_url": {"url": _to_data_url(expr_ref)}})
        user_blocks.append({"type": "text", "text": "Candidate generations follow, in order (index 0..n-1):"})
        for c in candidates:
            user_blocks.append({"type": "image_url", "image_url": {"url": _to_data_url(c.path)}})

        verdict_raw = self._chat_json(system=system, user_blocks=user_blocks)
        verdict_raw["best_index"] = self._coerce_index(verdict_raw.get("best_index"), len(candidates), best_index)
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
                "Step 1 expects a clean unobstructed character head turnaround "
                "(front / left-45 / left-side / back) on white. No kigurumi shell yet."
            )
        elif step == 2:
            target = (
                "Step 2 expects an animegao kigurumi head shell turnaround "
                "(front / left-45 / left-side / back) on white — hard face shell, "
                "fixed expression, real wig, large socketed eyes."
            )
        else:
            target = "Step 3 expects a clean product-photo four-view of the kigurumi head shell."

        return (
            f"{target}\n\n"
            f"You have {n_candidates} candidate(s). Choose the one that best matches the target character "
            "(hairstyle, hair color, ear position, eye color, temperament) AND the target expression. "
            "Then decide:\n"
            "- verdict = 'accept' if the best candidate is good enough overall, OR\n"
            "- verdict = 'refine' if a single targeted fix is required.\n"
            f"Valid refine_key values: {refinement_keys}\n"
            "Return JSON only with shape: "
            '{"best_index": <int>, "verdict": "accept"|"refine", "refine_key": "<one of valid keys or null>", '
            '"notes": "<short reason>"}'
        )

    def _final_pick(
        self, *, step: int, candidates: list[Candidate], refs: list[Path],
        char_info: str, expr_ref: Path,
    ) -> Candidate:
        """After all iterations end, pick the single best across every candidate.

        Implements the spec rule: "检查结束后从生成的图片对比，选择效果最好的图片".
        """
        if len(candidates) == 1:
            return candidates[0]

        if step == 1:
            target = "Step 1 — clean unobstructed character head turnaround on white."
        elif step == 2:
            target = "Step 2 — animegao kigurumi head shell turnaround on white."
        else:
            target = "Step 3 — product-photo style kigurumi shell four-view on white."

        system = "You are a strict art director making a final pick. Return JSON only."
        blocks: list[dict] = [
            {"type": "text", "text": (
                f"{target}\n\n"
                f"From {len(candidates)} candidates produced across multiple iterations, "
                "pick the single image that best matches the target character and target expression. "
                "Trade off identity fidelity, expression match, structural consistency across the four "
                "views, and kigurumi-appropriate styling. "
                'Return: {"best_index": <int>, "notes": "<short reason>"}'
            )},
        ]
        if char_info:
            blocks.append({"type": "text", "text": f"Target character info:\n{char_info}"})
        if refs:
            blocks.append({"type": "text", "text": "Target references:"})
            for p in refs:
                blocks.append({"type": "image_url", "image_url": {"url": _to_data_url(p)}})
        if expr_ref:
            blocks.append({"type": "text", "text": "Target expression reference:"})
            blocks.append({"type": "image_url", "image_url": {"url": _to_data_url(expr_ref)}})
        blocks.append({"type": "text", "text": f"Candidates (index 0..{len(candidates)-1}):"})
        for i, c in enumerate(candidates):
            blocks.append({"type": "text", "text": f"index {i}: step{c.step} iter{c.iteration} key={c.prompt_key}"})
            blocks.append({"type": "image_url", "image_url": {"url": _to_data_url(c.path)}})
        try:
            data = self._chat_json(system=system, user_blocks=blocks)
            idx = self._coerce_index(data.get("best_index"), len(candidates), 0)
            return candidates[idx]
        except Exception:
            return candidates[-1]

    # ---- dataset selection ----

    def _select_similar(self, primary_ref: Path, char_info: str, run_dir: Path) -> list[Path]:
        folders = sorted(p for p in DATASET_DIR.iterdir() if p.is_dir())
        if not folders or self.cfg.similar_top_k <= 0:
            return []
        # Stage A: text-only prefilter on folder names.
        names = [f.name for f in folders]
        pre_pick = self._text_prefilter(char_info=char_info, names=names, top_n=min(8, len(names)))
        shortlisted = [DATASET_DIR / n for n in pre_pick if (DATASET_DIR / n).is_dir()]
        if not shortlisted:
            shortlisted = folders[: min(8, len(folders))]

        # Stage B: visual pick from the shortlist (each folder's first image).
        thumbs = [(folder, self._first_image(folder)) for folder in shortlisted]
        thumbs = [(folder, img) for folder, img in thumbs if img is not None]
        if not thumbs:
            return []
        final = self._vision_pick(primary_ref=primary_ref, char_info=char_info, thumbs=thumbs, k=self.cfg.similar_top_k)

        # Persist similar selections under run_dir/similar/.
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
        return out

    def _text_prefilter(self, *, char_info: str, names: list[str], top_n: int) -> list[str]:
        system = (
            "You match a target character to nearest entries in a shop's finished-product "
            "library by name only. Return JSON only."
        )
        prompt = (
            f"Target character info:\n{char_info}\n\n"
            f"Library folder names (format: franchise-character-variant):\n" + "\n".join(names) + "\n\n"
            f"Pick up to {top_n} folder names whose franchise/style/character feel most similar "
            "to the target. Prefer same franchise > same style > visual hint in name. "
            'Return: {"picks": ["<exact folder name>", ...]}'
        )
        try:
            data = self._chat_json(system=system, user_blocks=[{"type": "text", "text": prompt}])
            picks = data.get("picks", [])
            valid = [n for n in picks if n in names]
            return valid[:top_n]
        except Exception:
            return names[:top_n]

    def _vision_pick(
        self, *, primary_ref: Path, char_info: str, thumbs: list[tuple[Path, Path]], k: int,
    ) -> list[Path]:
        system = "You are an art director selecting similar finished kigurumi products. Return JSON only."
        blocks: list[dict] = [
            {"type": "text", "text": (
                f"Target character info:\n{char_info}\n\n"
                f"Below: first the TARGET character reference, then {len(thumbs)} shop products "
                "in order (index 0..n-1) with their folder names. "
                f"Pick 0 to {k} indices whose finished kigurumi style would best inform our reference. "
                "Prefer matches in hair color, face shape, eye style, overall vibe. "
                'Return: {"picks": [<int>...], "notes": "<short>"}'
            )},
            {"type": "text", "text": "TARGET reference:"},
            {"type": "image_url", "image_url": {"url": _to_data_url(primary_ref)}},
        ]
        for i, (folder, img) in enumerate(thumbs):
            blocks.append({"type": "text", "text": f"Candidate {i}: {folder.name}"})
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
        except Exception:
            return [folder for folder, _ in thumbs[: max(0, k)]]

    @staticmethod
    def _first_image(folder: Path) -> Path | None:
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            for p in sorted(folder.glob(f"*{ext}")):
                return p
        return None

    # ---- chat helper ----

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
                    temperature=0.2,
                )
                text = resp.choices[0].message.content or ""
                return _extract_json(text)
            except Exception as e:
                last_err = e
                time.sleep(1 + attempt)
        raise RuntimeError(f"reasoner JSON call failed: {last_err}")

    # ---- run housekeeping ----

    @staticmethod
    def _init_run_dir(label: str) -> Path:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = OUTPUT_DIR / f"{stamp}_{_safe_slug(label)}"
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    @staticmethod
    def _log(run_dir: Path, name: str, content: str) -> None:
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
