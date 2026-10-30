"""Normaliza la exportación agregada de encuestas docentes de 2020."""

from __future__ import annotations

import io
import numbers
import re
import unicodedata
from typing import Any

import pandas as pd

from encuestas import QUESTIONS

SHEETS = (
    ("Anuales", "Anual S.C", "Anual"),
    ("Primer Cuatrimestre", "Primer Cuatrimestre S.C", "1.er cuatrimestre"),
    ("Segundo_Cuatrimestre", "Segundo Cuatrimestre S.C", "2.º cuatrimestre"),
)


def _key(value: object) -> str:
    return " ".join(str(value).strip().casefold().split())


def _code(value: object) -> str:
    if isinstance(value, numbers.Real) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _question_key(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    return re.sub(r"[^\w]+", "", text, flags=re.UNICODE)


def _teacher_names(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    names = []
    for raw_name in re.split(r"\s+-\s+", str(value).strip()):
        parts = raw_name.split(",", maxsplit=1)
        name = " ".join((parts[1].strip(), parts[0].strip())) if len(parts) == 2 else raw_name.strip()
        if name:
            names.append(" ".join(name.title().split()))
    return names


def _teacher_mapping(workbook: pd.ExcelFile) -> dict[tuple[str, str, str], list[str]]:
    frame = pd.read_excel(workbook, sheet_name="Docentes comisiones")
    mapping: dict[tuple[str, str, str], list[str]] = {}
    for row in frame.itertuples(index=False, name=None):
        _, code, commission, teachers, period = row
        key = (_key(period), _code(code), _key(commission))
        mapping[key] = list(dict.fromkeys(_teacher_names(teachers)))
    return mapping


def parse_survey_2020(file_bytes: bytes, filename: str) -> dict[str, Any]:
    workbook = pd.ExcelFile(io.BytesIO(file_bytes))
    teacher_mapping = _teacher_mapping(workbook)
    question_ids = {_question_key(q["text"]): q["id"] for q in QUESTIONS}
    records: list[dict[str, Any]] = []
    source_rows = 0

    for sheet_name, mapping_period, period_label in SHEETS:
        frame = pd.read_excel(workbook, sheet_name=sheet_name)
        source_rows += len(frame)
        for row in frame.itertuples(index=False, name=None):
            materia_raw, code_raw, commission_raw, question_raw, _, answer_raw, count_raw = row
            question_id = question_ids.get(_question_key(question_raw))
            if not question_id:
                raise ValueError(f"Pregunta 2020 sin correspondencia: {question_raw}")
            if pd.isna(count_raw) or int(count_raw) <= 0:
                continue

            code = _code(code_raw)
            commission = str(commission_raw).strip()
            materia = str(materia_raw).strip()
            materia = re.sub(rf"\s*\(\s*{re.escape(code)}\s*\)\s*$", "", materia).strip()
            concept = f"{materia} ({code}) - Comisión: {commission} - {period_label}"
            teachers = teacher_mapping.get((_key(mapping_period), code, _key(commission)))
            if not teachers:
                teachers = ["Sin docente asignado"]
            answer = str(answer_raw).strip()
            quantity = int(count_raw)

            for teacher in teachers:
                records.append(
                    {
                        "id": f"2020-{len(records)}",
                        "docente": teacher,
                        "docenteClave": teacher.casefold(),
                        "cargo": "Sin asignar" if teacher == "Sin docente asignado" else "Docente",
                        "concepto": concept,
                        "materia": materia,
                        "codigoMateria": code,
                        "comision": commission,
                        "fechaInicio": None,
                        "fechaFin": None,
                        "cantidad": quantity,
                        "respuestas": {question_id: answer},
                        "puntajes": {},
                    }
                )

    return {
        "fuente": filename,
        "periodo": "2020 · anual y cuatrimestres",
        "preguntas": QUESTIONS,
        "registros": records,
        "encuestas_origen": source_rows,
    }
