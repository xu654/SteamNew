# utils/subscribe.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional


def load_map(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_map(path: Path, data: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def remember_group_umo(path: Path, group_id: str, umo: str) -> None:
    group_id = (group_id or "").strip()
    umo = (umo or "").strip()
    if not group_id or not umo:
        return

    data = load_map(path)
    if data.get(group_id) == umo:
        return
    data[group_id] = umo
    save_map(path, data)


def resolve_umo(path: Path, group_id: str) -> Optional[str]:
    data = load_map(path)
    return data.get(str(group_id).strip())