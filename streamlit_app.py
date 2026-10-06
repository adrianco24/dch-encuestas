"""Visor de encuestas docentes. Subí cada Excel descargado y filtrá por docente."""

from __future__ import annotations

import io
from html import escape
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from encuestas import (
    QUESTIONS,
    TONE_COLORS,
    answer_tone,
    count_answers,
    parse_survey,
    subjects_of,
    teachers_from,
)

st.set_page_config(page_title="Encuestas DCH", page_icon="📋", layout="wide")

SAMPLE = Path(__file__).resolve().parent / "anuales2023.xlsx"
PARSER_CACHE_VERSION = 2


@st.cache_data(show_spinner="Leyendo y agrupando el archivo…")
def load_from_bytes(file_bytes: bytes, filename: str, parser_version: int) -> dict:
    df = pd.read_excel(io.BytesIO(file_bytes))
    return parse_survey(df, filename)


def load_from_path(path: Path) -> dict:
    df = pd.read_excel(path)
    return parse_survey(df, path.name)


def load_from_uploads(uploads) -> dict:
    datasets = [
        load_from_bytes(upload.getvalue(), upload.name, PARSER_CACHE_VERSION)
        for upload in uploads
    ]
    questions = {
        question["id"]: question
        for dataset in datasets
        for question in dataset["preguntas"]
    }
    return {
        "fuente": " + ".join(dataset["fuente"] for dataset in datasets),
        "registros": [record for dataset in datasets for record in dataset["registros"]],
        "encuestas_origen": sum(dataset["encuestas_origen"] for dataset in datasets),
        "preguntas": list(questions.values()),
    }


def bar_chart(rows: list[tuple[str, int]]) -> alt.Chart:
    total = sum(n for _, n in rows) or 1
    frame = pd.DataFrame(
        {
            "Respuesta": [label for label, _ in rows],
            "Cantidad": [n for _, n in rows],
            "Porcentaje": [round(100 * n / total) for _, n in rows],
            "color": [TONE_COLORS[answer_tone(label)] for label, _ in rows],
        }
    )
    return (
        alt.Chart(frame)
        .mark_bar(size=18)
        .encode(
            x=alt.X("Cantidad:Q", title=None),
            y=alt.Y("Respuesta:N", sort="-x", title=None),
            color=alt.Color("color:N", scale=None, legend=None),
            tooltip=["Respuesta", "Cantidad", "Porcentaje"],
        )
        .properties(height=max(120, 28 * len(frame) + 40))
    )


def overview_chart(
    records: list[dict], questions: list[dict]
) -> alt.Chart | None:
    chart_rows = []
    question_order = []
    answer_labels = []

    for question in questions:
        answers = count_answers(records, question["id"])
        total = sum(count for _, count in answers)
        if not total:
            continue

        question_label = f"{question['short']} (n={total})"
        question_order.append(question_label)
        for answer, count in answers:
            if answer not in answer_labels:
                answer_labels.append(answer)
            chart_rows.append(
                {
                    "Pregunta": question_label,
                    "Respuesta": answer,
                    "Cantidad": count,
                    "Proporcion": count / total,
                    "Porcentaje": round(100 * count / total),
                }
            )

    if not chart_rows:
        return None

    colors = [TONE_COLORS.get(answer_tone(label), TONE_COLORS["neutro"]) for label in answer_labels]
    frame = pd.DataFrame(chart_rows)
    return (
        alt.Chart(frame)
        .mark_bar()
        .encode(
            x=alt.X(
                "Proporcion:Q",
                stack="zero",
                scale=alt.Scale(domain=[0, 1]),
                axis=alt.Axis(format="%", values=[0, 0.25, 0.5, 0.75, 1], title="Porcentaje"),
            ),
            y=alt.Y("Pregunta:N", sort=question_order, title=None),
            color=alt.Color(
                "Respuesta:N",
                scale=alt.Scale(domain=answer_labels, range=colors),
                legend=alt.Legend(title="Respuesta", orient="bottom", columns=5),
            ),
            tooltip=[
                alt.Tooltip("Pregunta:N", title="Pregunta"),
                alt.Tooltip("Respuesta:N", title="Respuesta"),
                alt.Tooltip("Cantidad:Q", title="Respuestas"),
                alt.Tooltip("Porcentaje:Q", title="Porcentaje", format=".0f"),
            ],
        )
        .properties(height=max(300, 36 * len(question_order)))
    )


def answer_summary(rows: list[tuple[str, int]], total: int) -> str:
    tints = {
        "excelente": "#e5eee8",
        "buena": "#e5eff7",
        "regular": "#f5eddc",
        "deficiente": "#f4e5e2",
        "sin-opinion": "#eeeae5",
        "neutro": "#eeeae5",
    }
    items = []
    for index, (label, count) in enumerate(sorted(rows, key=lambda row: row[1], reverse=True)):
        tone = answer_tone(label)
        color = TONE_COLORS.get(tone, TONE_COLORS["neutro"])
        tint = tints.get(tone, tints["neutro"])
        percentage = round(100 * count / total)
        leading = " leading" if index == 0 else ""
        items.append(
            f'<div class="summary-item{leading}" style="--answer-color:{color};--answer-tint:{tint}">'
            f'<span class="summary-label">{escape(label)}</span>'
            f'<strong>{count} <span>({percentage}%)</span></strong></div>'
        )
    return f'<div class="answer-summary">{"".join(items)}</div>'


st.markdown(
    """
    <style>
      .block-container { padding-top: 1.4rem; }
      h1, h2, h3 { font-weight: 650; }
            .answer-summary {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
                gap: 8px;
                margin: 14px 0 8px;
            }
            .summary-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 10px;
                min-width: 0;
                padding: 8px 10px;
                border-left: 3px solid var(--answer-color);
                background: var(--answer-tint);
                font-size: 0.9rem;
            }
            .summary-label { min-width: 0; overflow-wrap: anywhere; }
            .summary-item strong {
                flex: 0 0 auto;
                color: var(--answer-color);
                white-space: nowrap;
            }
            .summary-item strong span { font-size: 0.85em; font-weight: 600; }
            .summary-item.leading { padding-block: 10px; font-size: 0.97rem; }
            .summary-item.leading strong { font-size: 1.08rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.title("Encuestas DCH")
    st.caption("Cargá uno o varios Excel de resultados.")
    if "new_format_upload" not in st.session_state:
        st.session_state.new_format_upload = False
    if st.session_state.new_format_upload:
        uploads = st.file_uploader(
            "Archivo de encuestas formato 2024",
            type=["xlsx", "xls"],
            accept_multiple_files=True,
            key="new_format_files",
        )
        if st.button("Volver a carga anterior", use_container_width=True):
            st.session_state.new_format_upload = False
            st.rerun()
    else:
        uploads = st.file_uploader(
            "Agregar archivos de resultados",
            type=["xlsx", "xls"],
            accept_multiple_files=True,
            key="legacy_format_files",
        )
        if st.button("Cargar nuevo formato 2024", use_container_width=True):
            st.session_state.new_format_upload = True
            st.rerun()
    use_sample = False
    if not uploads and SAMPLE.exists():
        use_sample = st.checkbox("Usar anuales2023.xlsx de ejemplo", value=True)

data = None
error = None
if uploads:
    try:
        data = load_from_uploads(uploads)
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
elif use_sample:
    try:
        data = load_from_path(SAMPLE)
    except Exception as exc:  # noqa: BLE001
        error = str(exc)

if error:
    st.error(error)
    st.stop()

if data is None:
    st.info("Subí un Excel de encuestas para empezar.")
    st.stop()

records = data["registros"]
data_questions = data["preguntas"]
teachers = teachers_from(records)

with st.sidebar:
    st.metric("Evaluaciones", len(records))
    st.metric("Docentes", len(teachers))
    st.caption(f"Origen: {data['fuente']} · {data['encuestas_origen']} filas")

st.subheader("Seleccionar docente")
search_col, teacher_col = st.columns([1, 1.6])
with search_col:
    query = st.text_input("Buscar docente", placeholder="Nombre o cargo")
filtered = teachers
if query.strip():
    q = query.strip().casefold()
    filtered = [
        teacher
        for teacher in teachers
        if q in teacher["nombre"].casefold()
        or any(q in cargo.casefold() for cargo in teacher["cargos"])
    ]
labels = [
    f"{teacher['nombre']} ({', '.join(teacher['cargos']) or 's/cargo'}) — {teacher['respuestas']} resp."
    for teacher in filtered
]
with teacher_col:
    choice = st.selectbox(
        "Docente",
        options=["— Elegí un docente —"] + labels,
    )

if choice == "— Elegí un docente —":
    st.header("Resultados de encuestas")
    st.write("Elegí un docente arriba para ver las respuestas agrupadas por pregunta.")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Docente": t["nombre"],
                    "Cargo": ", ".join(t["cargos"]),
                    "Respuestas": t["respuestas"],
                    "Cátedras": t["materias"],
                }
                for t in teachers
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.stop()

selected = filtered[labels.index(choice)]
selected_records = [r for r in records if r["docenteClave"] == selected["clave"]]
subject_options = sorted({r["concepto"] for r in selected_records}, key=lambda s: s.casefold())
subject_col, _ = st.columns([1, 1.6])
with subject_col:
    subject = st.selectbox("Cátedra / comisión", ["Todas las cátedras"] + subject_options)
visible = (
    selected_records
    if subject == "Todas las cátedras"
    else [r for r in selected_records if r["concepto"] == subject]
)

st.header(selected["nombre"])
st.caption(" · ".join(selected["cargos"]) if selected["cargos"] else "Sin cargo informado")

c1, c2, c3 = st.columns(3)
c1.metric("Respuestas", len(visible))
c2.metric("Cátedras", selected["materias"] if subject == "Todas las cátedras" else 1)
c3.metric("Preguntas", len(data_questions))

st.subheader("Resumen de respuestas")
st.caption(
    "Distribución porcentual por pregunta. El total de respuestas aparece junto al nombre; "
    "pasá el cursor para ver cantidades y porcentajes."
)
overview = overview_chart(visible, data_questions)
if overview is None:
    st.info("No hay respuestas para mostrar en este recorte.")
else:
    st.altair_chart(overview, use_container_width=True)

st.subheader("Detalle por pregunta")
ejes: list[str] = []
for question in data_questions:
    if question["eje"] not in ejes:
        ejes.append(question["eje"])

for eje in ejes:
    st.subheader(eje)
    for question in (q for q in data_questions if q["eje"] == eje):
        rows = count_answers(visible, question["id"])
        with st.container(border=True):
            st.markdown(f"**{question['short']}**")
            st.caption(question["text"])
            if not rows:
                st.write("Sin respuestas en este recorte.")
            else:
                total = sum(n for _, n in rows)
                st.markdown(answer_summary(rows, total), unsafe_allow_html=True)
                st.altair_chart(bar_chart(rows), use_container_width=True)

st.subheader("Cátedras evaluadas")
st.dataframe(
    pd.DataFrame(
        [{"Asignatura / comisión": row["concepto"], "Respuestas": row["n"]} for row in subjects_of(selected_records)]
    ),
    hide_index=True,
    use_container_width=True,
)
