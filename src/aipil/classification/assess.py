"""Deterministic composites from extracted component ratings (see config/assessment.yaml).

Keeping the arithmetic in code (rather than asking an LLM for a single number) makes every
composite reproducible and explainable from its components.
"""
from __future__ import annotations

from aipil.extraction.schema import assessment_cfg, taxonomy

IMPLEMENTED_ROLES = {"implemented", "baseline", "compared"}


def sophistication(components: dict[str, int]) -> float:
    vals = list(components.values())
    return round(sum(vals) / (3 * len(vals)) * 10, 1) if vals else None


def max_algorithm_level(algorithms: list[dict]) -> int:
    terms = taxonomy()["dimensions"]["algorithm"]["terms"]
    levels = [terms.get(a["canonical"], {}).get("level", 2) for a in algorithms if a["role"] in IMPLEMENTED_ROLES]
    return max(levels) if levels else 1


def difficulty_tier(prereq: dict[str, int], alg_level: int) -> tuple[str, str]:
    py, ms, ml = prereq["python"], prereq["math_stats"], prereq["ml"]
    core = py + ms + ml
    mx = max(py, ms, ml)
    if ml == 3 or (alg_level == 3 and ml >= 2) or (mx == 3 and core >= 7):
        why = []
        if ml == 3:
            why.append("substantial ML background (deep/sequence/generative models)")
        if alg_level == 3:
            why.append("uses advanced model architectures")
        if mx == 3 and core >= 7:
            why.append("high combined Python/math/ML prerequisites")
        return "Advanced", "; ".join(why)
    if mx <= 1 or (core <= 4 and alg_level <= 1):
        return "Beginner", "basic Python and introductory ML are sufficient; beginner-level algorithms"
    return "Intermediate", (f"moderate prerequisites (Python {py}, math/stats {ms}, ML {ml} on a 1-3 scale; "
                            f"highest algorithm level {alg_level})")


def reproduction_band(components: dict[str, int]) -> tuple[int, str, str]:
    total = sum(components.values())
    for b in assessment_cfg()["reproduction_effort"]["bands"]:
        if total <= b["max"]:
            return total, b["label"], b["estimate"]
    b = assessment_cfg()["reproduction_effort"]["bands"][-1]
    return total, b["label"], b["estimate"]


def adoption_band(criteria: dict[str, bool]) -> tuple[int, str]:
    n = sum(bool(v) for v in criteria.values())
    label = "Not ready"
    for thresh, lab in sorted(assessment_cfg()["adoption_readiness"]["bands"].items()):
        if n >= thresh:
            label = lab
    return n, label


# ----------------------------------------------------------------- Python level (criteria in config/assessment.yaml)
DEEP_FAMILIES = {"neural", "neural_vision", "neural_sequence", "transformer", "generative", "graph", "multimodal"}
DL_TOOLS = {"pytorch", "tensorflow", "keras"}
BACKEND_TOOLS = {"flask", "fastapi", "docker", "javascript", "vector_db", "langchain"}
APP_TOOLS = {"streamlit", "gradio", "flask", "fastapi"}
API_TOOLS = {"llm_api", "yfinance"}
PRETRAINED_ALGS = {"llm", "sentence_transformer", "speech_model", "clip", "ts_foundation_model", "bert", "yolo",
                   "resnet", "efficientnet", "mobilenet", "vgg", "densenet", "vision_transformer", "pose_model", "ocr_model",
                   "face_detection", "depth_estimation"}


def python_level(ex: dict) -> tuple[int, list[str]]:
    """Deterministic Python prerequisite from an extraction dict. Returns (level, satisfied criterion keys)."""
    terms = taxonomy()["dimensions"]["algorithm"]["terms"]
    aliases = taxonomy().get("aliases") or {}

    def norm(dim, slug):
        a = aliases.get(f"{dim}:{slug}")
        return a.split(":", 1)[1] if a else slug

    def tagset(key, dim):
        return {norm(dim, t["term"]) for t in ex.get(key, []) if t["evidence_level"] in ("confirmed", "inferred")}
    tools, methods, paradigms = tagset("tools", "tool"), tagset("methods", "method"), tagset("paradigms", "paradigm")
    used = [norm("algorithm", a["canonical"]) for a in ex.get("algorithms", []) if a["role"] in IMPLEMENTED_ROLES]
    soph = {k: v["score"] for k, v in ex.get("sophistication", {}).items()}
    deep3 = [a for a in used if terms.get(a, {}).get("family") in DEEP_FAMILIES and terms.get(a, {}).get("level") == 3]
    l3 = {
        "trains_deep_model": bool(deep3) and bool(tools & DL_TOOLS or "fine_tuning" in methods),
        "system_engineering": soph.get("engineering", 0) >= 3,
        "backend_stack": len(tools & BACKEND_TOOLS) >= 2,
        "reinforcement_learning": "q_learning" in used or "reinforcement" in paradigms,
    }
    l2 = {
        "interactive_app": bool(tools & APP_TOOLS) or "deployment" in methods or soph.get("engineering", 0) >= 2,
        "external_data_access": bool(tools & API_TOOLS) or bool(methods & {"api_integration", "web_scraping"}),
        "pretrained_models": bool(set(used) & PRETRAINED_ALGS) or "huggingface" in tools,
        "multi_source_pipeline": "data_fusion" in methods and soph.get("data_processing", 0) >= 2,
        "custom_pipeline": soph.get("methodological_breadth", 0) >= 2 and soph.get("data_processing", 0) >= 2,
    }
    if any(l3.values()):
        return 3, [k for k, v in l3.items() if v]
    if any(l2.values()):
        return 2, [k for k, v in l2.items() if v]
    return 1, ["default"]
