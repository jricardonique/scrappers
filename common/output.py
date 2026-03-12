
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

def ts() -> str: return datetime.utcnow().strftime('%Y%m%d_%H%M%S')

def run_dir(base: Path) -> Path:
    d = base / ts(); d.mkdir(parents=True, exist_ok=True); return d

def write_json(path: Path, data: Any):
    with path.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
