"""Normaliza exportaciones de encuestas docentes (Excel variable, 1+ docentes por fila)."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

QUESTIONS = [
    {
        "id": "informacion_inicial",
        "eje": "Organización",
        "short": "Información al inicio del curso",
        "text": "¿Cómo fue la información proporcionada por el Docente al inicio del curso, respecto del desarrollo de la asignatura, material de estudio o bibliografía básica, parciales y evaluación?",
    },
    {
        "id": "bibliografia",
        "eje": "Organización",
        "short": "Disponibilidad de bibliografía",
        "text": "La bibliografía indicada por el Docente ¿estuvo disponible para los alumnos?",
    },
    {
        "id": "relacion_programa",
        "eje": "Organización",
        "short": "Relación con el programa",
        "text": "¿Existió relación entre el dictado de clases y el programa de la asignatura?",
    },
    {
        "id": "claridad_exposicion",
        "eje": "Dictado",
        "short": "Claridad y exposición",
        "text": "Califique el desarrollo del curso de acuerdo a claridad y exposición del Docente",
    },
    {
        "id": "debate_ideas",
        "eje": "Dictado",
        "short": "Debate e intercambio de ideas",
        "text": "Califique el desarrollo del curso de acuerdo con la capacidad para motivar el debate y el intercambio de ideas",
    },
    {
        "id": "temas_parciales",
        "eje": "Evaluación",
        "short": "Temas de parciales vs. clases",
        "text": "¿Los temas de exámenes parciales estuvieron acordes a los contenidos impartidos en clase?",
    },
    {
        "id": "consignas_claras",
        "eje": "Evaluación",
        "short": "Claridad de consignas",
        "text": "¿Las consignas de los exámenes parciales fueron presentadas en forma clara?",
    },
    {
        "id": "asistencia",
        "eje": "Cumplimiento",
        "short": "Asistencia a clases",
        "text": "¿Cómo fue la asistencia del Docente a las clases?",
    },
    {
        "id": "horarios",
        "eje": "Cumplimiento",
        "short": "Respeto de horarios",
        "text": "¿Se respetaron los horarios de clases acordados?",
    },
    {
        "id": "recursos_didacticos",
        "eje": "Dictado",
        "short": "Recursos didácticos",
        "text": "¿Cómo calificaría la utilización de los recursos didácticos? (por ejemplo uso del pizarrón, retroproyector, otros).",
    },
    {
        "id": "disposicion",
        "eje": "Dictado",
        "short": "Disposición a responder",
        "text": "¿Cuál fue la disposición del Docente, para responder las preguntas e inquietudes de los alumnos?",
    },
]

TEACHER_RE = re.compile(r"^(.*?)\s*\(([^)]+)\)\s*$")
SUBJECT_RE = re.compile(
    r"^(.*?)\s*\(([^)]+)\)\s*-\s*Comisión:\s*(.+)$",
    re.IGNORECASE,
)

TONE = {
    "muy buena": "excelente",
    "en general si": "excelente",
    "estrictamente": "excelente",
    "buena": "buena",
    "medianamente": "buena",
    "regular": "regular",
    "poco": "regular",
    "deficiente": "deficiente",
    "no": "deficiente",
    "no opina": "sin-opinion",
}

TONE_COLORS = {
    "excelente": "#2f6b4f",
    "buena": "#3d7a6a",
    "regular": "#c0841a",
    "deficiente": "#b33a32",
    "sin-opinion": "#8a8176",
    "neutro": "#8a8176",
}


def _norm_text(value: object) -> str:
    text = str(value)
    text = re.sub(r"\.\d+$", "", text)
    text = re.sub(r"^código\s*-\s*", "", text, flags=re.IGNORECASE)
    text = text.replace("¿", "").replace("?", "").replace(";", "")
    text = re.sub(r"[.\s]+$", "", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _is_code_col(name: object) -> bool:
    return str(name).lower().startswith("código") or str(name).lower().startswith("codigo")


def _is_teacher_col(name: object) -> bool:
    n = str(name).lower()
    return n.startswith("elemento evaluado") and "origen" not in n


def _find_col(columns: list[Any], *needles: str) -> int | None:
    lowered = [str(c).lower() for c in columns]
    for needle in needles:
        for i, name in enumerate(lowered):
            if name == needle or name.startswith(needle):
                return i
    return None


def _question_id_for(col_name: object) -> str | None:
    if _is_code_col(col_name) or _is_teacher_col(col_name):
        return None
    col_n = _norm_text(col_name)
    if not col_n:
        return None
    best: tuple[int, str] | None = None
    for question in QUESTIONS:
        qn = _norm_text(question["text"])
        if col_n.startswith(qn[:48]) or qn[:48] in col_n:
            score = min(len(col_n), len(qn))
            if best is None or score > best[0]:
                best = (score, question["id"])
    return best[1] if best else None


def norm_label(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def parse_teacher(raw: str) -> tuple[str, str]:
    match = TEACHER_RE.match(raw)
    if not match:
        return raw, ""
    return match.group(1).strip(), match.group(2).strip()


def parse_subject(raw: str) -> tuple[str, str, str]:
    match = SUBJECT_RE.match(raw)
    if not match:
        return raw, "", ""
    return match.group(1).strip(), match.group(2).strip(), match.group(3).strip()


def answer_key(label: str) -> str:
    return " ".join(label.lower().replace("sí", "si").split())


def answer_tone(label: str) -> str:
    return TONE.get(answer_key(label), "neutro")


def _teacher_slots(columns: list[Any]) -> list[dict[str, Any]]:
    teacher_idxs = [i for i, name in enumerate(columns) if _is_teacher_col(name)]
    date_idx = _find_col(columns, "fecha de inicio", "fecha fin")
    slots: list[dict[str, Any]] = []
    for i, t_idx in enumerate(teacher_idxs):
        end = teacher_idxs[i + 1] if i + 1 < len(teacher_idxs) else (date_idx if date_idx is not None else len(columns))
        mapping: dict[str, int] = {}
        for col_i in range(t_idx + 1, end):
            qid = _question_id_for(columns[col_i])
            if qid and qid not in mapping:
                mapping[qid] = col_i
        slots.append({"teacher_col": t_idx, "questions": mapping})
    return slots


def parse_survey(df: pd.DataFrame, fuente: str = "") -> dict[str, Any]:
    columns = list(df.columns)
    concepto_idx = _find_col(columns, "concepto evaluado")
    if concepto_idx is None:
        raise ValueError(
            "No encontré la columna 'Concepto evaluado'. "
            "Subí el Excel de resultados de encuestas (el mismo tipo de exportación)."
        )
    fecha_inicio_idx = _find_col(columns, "fecha de inicio")
    fecha_fin_idx = _find_col(columns, "fecha fin")
    slots = _teacher_slots(columns)
    if not slots:
        raise ValueError("No encontré columnas de 'Elemento evaluado' (docentes).")

    records: list[dict[str, Any]] = []
    for row_i, row in df.iterrows():
        concepto = norm_label(row.iloc[concepto_idx]) or ""
        materia, codigo, comision = parse_subject(concepto)
        fecha_inicio = None
        fecha_fin = None
        if fecha_inicio_idx is not None:
            ts = pd.to_datetime(row.iloc[fecha_inicio_idx], errors="coerce")
            if not pd.isna(ts):
                fecha_inicio = ts.strftime("%Y-%m-%d")
        if fecha_fin_idx is not None:
            ts = pd.to_datetime(row.iloc[fecha_fin_idx], errors="coerce")
            if not pd.isna(ts):
                fecha_fin = ts.strftime("%Y-%m-%d")

        for slot in slots:
            teacher_raw = norm_label(row.iloc[slot["teacher_col"]])
            if not teacher_raw:
                continue
            nombre, cargo = parse_teacher(teacher_raw)
            answers: dict[str, str] = {}
            for qid, col_i in slot["questions"].items():
                label = norm_label(row.iloc[col_i])
                if label:
                    answers[qid] = label
            if not answers:
                continue
            records.append(
                {
                    "id": f"{row_i}-{slot['teacher_col']}",
                    "docente": nombre,
                    "docenteClave": teacher_raw,
                    "cargo": cargo,
                    "concepto": concepto,
                    "materia": materia,
                    "codigoMateria": codigo,
                    "comision": comision,
                    "fechaInicio": fecha_inicio,
                    "fechaFin": fecha_fin,
                    "respuestas": answers,
                }
            )

    return {
        "fuente": fuente,
        "preguntas": QUESTIONS,
        "registros": records,
        "encuestas_origen": int(df.shape[0]),
    }


def teachers_from(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for rec in records:
        entry = grouped.setdefault(
            rec["docenteClave"],
            {
                "clave": rec["docenteClave"],
                "nombre": rec["docente"],
                "cargos": set(),
                "respuestas": 0,
                "materias": set(),
            },
        )
        entry["respuestas"] += 1
        if rec.get("cargo"):
            entry["cargos"].add(rec["cargo"])
        entry["materias"].add(rec["concepto"])
    result = []
    for entry in grouped.values():
        result.append(
            {
                "clave": entry["clave"],
                "nombre": entry["nombre"],
                "cargos": sorted(entry["cargos"]),
                "respuestas": entry["respuestas"],
                "materias": len(entry["materias"]),
            }
        )
    result.sort(key=lambda t: t["nombre"].casefold())
    return result


def count_answers(records: list[dict[str, Any]], question_id: str) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for rec in records:
        label = rec["respuestas"].get(question_id)
        if not label:
            continue
        counts[label] = counts.get(label, 0) + 1
    return sorted(counts.items(), key=lambda item: item[1], reverse=True)


def subjects_of(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for rec in records:
        counts[rec["concepto"]] = counts.get(rec["concepto"], 0) + 1
    return [
        {"concepto": concepto, "n": n}
        for concepto, n in sorted(counts.items(), key=lambda item: item[1], reverse=True)
    ]
