"""Importação/exportação de presets em .json (compatível com o preset-studio web e CubeControl/ToneHub)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import protocol as P
from .settings import data_dir

SINGLE_FORMAT = "cuvave-preset-studio-preset-v1"
LIBRARY_FORMAT = "cuvave-preset-studio-library-v1"
TONEHUB_FORMAT = "tonehub-cube-baby-bank-v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def preset_to_dict(name: str, params: dict, notes: str = "") -> dict:
    out = {"format": SINGLE_FORMAT, "name": name}
    if notes:
        out["notes"] = notes
    out["params"] = P.clamp_params(params)
    out["exportedAt"] = _now()
    return out


def parse_import(raw) -> tuple[list[dict], list[str]]:
    """Retorna (lista de {'name','params'}, avisos). Levanta ValueError se não reconhecer."""
    if not isinstance(raw, dict):
        raise ValueError("O arquivo não é um JSON de preset válido.")
    warnings: list[str] = []
    fmt = raw.get("format")

    if fmt == SINGLE_FORMAT:
        return [{"name": str(raw.get("name") or "Preset importado"), "params": P.clamp_params(raw.get("params") or {})}], warnings

    if fmt == LIBRARY_FORMAT:
        items = raw.get("presets") or []
        return [
            {"name": str(it.get("name") or f"Preset {i + 1}"), "params": P.clamp_params(it.get("params") or {})}
            for i, it in enumerate(items)
        ], warnings

    if fmt == TONEHUB_FORMAT:
        slots = raw.get("slots") or []
        presets = [
            {"name": f"Importado (slot {s.get('slot', '?')})", "params": P.clamp_params(s)} for s in slots
        ]
        if presets:
            warnings.append("Importado de um banco no formato CubeControl/ToneHub.")
        return presets, warnings

    if any(isinstance(raw.get(n), (int, float)) for n in P.PARAM_NAMES):
        warnings.append("Formato não reconhecido; parâmetros lidos pelo nome (type, gain, tone...).")
        return [{"name": str(raw.get("name") or "Preset importado"), "params": P.clamp_params(raw)}], warnings

    raise ValueError("Não reconheci esse arquivo como preset do CUBE Baby.")


def load_file(path: str | Path) -> tuple[list[dict], list[str]]:
    with open(path, "r", encoding="utf-8") as fh:
        return parse_import(json.load(fh))


def save_file(path: str | Path, name: str, params: dict, notes: str = "") -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(preset_to_dict(name, params, notes), fh, indent=2, ensure_ascii=False)


# ---- biblioteca local (uma pasta com um .json por preset) -------------------------

def library_dir() -> Path:
    d = data_dir() / "biblioteca"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _slug(name: str) -> str:
    return re.sub(r"[^\w\-]+", "_", name, flags=re.UNICODE).strip("_")[:60] or "preset"


def library_list() -> list[tuple[Path, str, dict]]:
    out = []
    for f in sorted(library_dir().glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            presets, _ = load_file(f)
        except Exception:
            continue
        if presets:
            out.append((f, presets[0]["name"], presets[0]["params"]))
    return out


def library_add(name: str, params: dict) -> Path:
    base = library_dir() / f"{_slug(name)}.json"
    path, n = base, 2
    while path.exists():
        path = base.with_name(f"{base.stem}_{n}.json"); n += 1
    save_file(path, name, params)
    return path
