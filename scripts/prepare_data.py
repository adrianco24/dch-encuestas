"""Convierte un Excel de encuestas en public/encuestas.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from encuestas import parse_survey  # noqa: E402
import pandas as pd  # noqa: E402

SOURCE = ROOT / "anuales2023.xlsx"
OUT = ROOT / "public" / "encuestas.json"


def main() -> None:
    df = pd.read_excel(SOURCE)
    payload = parse_survey(df, SOURCE.name)
    payload["periodo"] = "2023"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"Escritos {len(payload['registros'])} registros de {payload['encuestas_origen']} encuestas en {OUT}")


if __name__ == "__main__":
    main()
