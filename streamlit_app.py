"""Visor de encuestas docentes. Subí cada Excel descargado y filtrá por docente."""

from __future__ import annotations

import io
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


@st.cache_data(show_spinner="Leyendo y agrupando el archivo…")
def load_from_bytes(file_bytes: bytes, filename: str) -> dict:
    df = pd.read_excel(io.BytesIO(file_bytes))
    return parse_survey(df, filename)


def load_from_path(path: Path) -> dict:
    df = pd.read_excel(path)
    return parse_survey(df, path.name)


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


st.markdown(
    """
    <style>
      .block-container { padding-top: 1.4rem; }
      h1, h2, h3 { font-weight: 650; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.title("Encuestas DCH")
    st.caption("Cada vez que bajes un Excel de resultados, subilo acá. El archivo puede cambiar de año o de cantidad de docentes.")
    uploaded = st.file_uploader("Archivo de resultados", type=["xlsx", "xls"])
    use_sample = False
    if uploaded is None and SAMPLE.exists():
        use_sample = st.checkbox("Usar anuales2023.xlsx de ejemplo", value=True)

data = None
error = None
if uploaded is not None:
    try:
        data = load_from_bytes(uploaded.getvalue(), uploaded.name)
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
teachers = teachers_from(records)

with st.sidebar:
    st.metric("Evaluaciones", len(records))
    st.metric("Docentes", len(teachers))
    st.caption(f"Origen: {data['fuente']} · {data['encuestas_origen']} filas")
    query = st.text_input("Buscar docente")
    filtered = teachers
    if query.strip():
        q = query.strip().casefold()
        filtered = [
            t
            for t in teachers
            if q in t["nombre"].casefold() or any(q in c.casefold() for c in t["cargos"])
        ]
    labels = [
        f"{t['nombre']} ({', '.join(t['cargos']) or 's/cargo'}) — {t['respuestas']} resp."
        for t in filtered
    ]
    choice = st.selectbox("Docente", options=["— Elegí un docente —"] + labels)

if choice == "— Elegí un docente —":
    st.header("Resultados de encuestas")
    st.write("Elegí un docente en la barra lateral para ver las respuestas agrupadas por pregunta.")
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
c3.metric("Preguntas", len(QUESTIONS))

ejes: list[str] = []
for question in QUESTIONS:
    if question["eje"] not in ejes:
        ejes.append(question["eje"])

for eje in ejes:
    st.subheader(eje)
    for question in (q for q in QUESTIONS if q["eje"] == eje):
        rows = count_answers(visible, question["id"])
        with st.container(border=True):
            st.markdown(f"**{question['short']}**")
            st.caption(question["text"])
            if not rows:
                st.write("Sin respuestas en este recorte.")
            else:
                total = sum(n for _, n in rows)
                st.altair_chart(bar_chart(rows), use_container_width=True)
                st.caption(" · ".join(f"{label}: {n} ({round(100 * n / total)}%)" for label, n in rows))

st.subheader("Cátedras evaluadas")
st.dataframe(
    pd.DataFrame(
        [{"Asignatura / comisión": row["concepto"], "Respuestas": row["n"]} for row in subjects_of(selected_records)]
    ),
    hide_index=True,
    use_container_width=True,
)
