import { useEffect, useMemo, useState } from "react";
import type { SurveyData, SurveyRecord } from "./types";
import {
  answerTone,
  countAnswers,
  subjectsOf,
  teachersFrom,
} from "./stats";

export default function App() {
  const [data, setData] = useState<SurveyData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [teacherKey, setTeacherKey] = useState("");
  const [subject, setSubject] = useState("todas");

  useEffect(() => {
    fetch("/encuestas.json")
      .then((res) => {
        if (!res.ok) throw new Error("No se pudo leer encuestas.json");
        return res.json();
      })
      .then(setData)
      .catch((err: Error) => setError(err.message));
  }, []);

  const teachers = useMemo(() => (data ? teachersFrom(data.registros) : []), [data]);
  const filteredTeachers = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return teachers;
    return teachers.filter(
      (t) =>
        t.nombre.toLowerCase().includes(q) ||
        t.cargos.some((c) => c.toLowerCase().includes(q)),
    );
  }, [teachers, query]);

  const selectedRecords = useMemo(() => {
    if (!data || !teacherKey) return [] as SurveyRecord[];
    return data.registros.filter((r) => r.docenteClave === teacherKey);
  }, [data, teacherKey]);

  const visibleRecords = useMemo(() => {
    if (subject === "todas") return selectedRecords;
    return selectedRecords.filter((r) => r.concepto === subject);
  }, [selectedRecords, subject]);

  const selectedTeacher = teachers.find((t) => t.clave === teacherKey);
  const subjectOptions = useMemo(
    () => [...new Set(selectedRecords.map((r) => r.concepto))].sort((a, b) => a.localeCompare(b, "es")),
    [selectedRecords],
  );
  const subjectRows = useMemo(() => subjectsOf(selectedRecords), [selectedRecords]);

  if (error) {
    return <p className="empty">Error: {error}. Ejecutá <code>python scripts/prepare_data.py</code>.</p>;
  }
  if (!data) {
    return <p className="empty">Cargando encuestas…</p>;
  }

  const ejes = [...new Set(data.preguntas.map((q) => q.eje))];

  return (
    <div className="app">
      <aside className="sidebar">
        <div>
          <h1 className="brand">Encuestas DCH</h1>
          <p className="brand-sub">
            {data.periodo} · {data.registros.length} evaluaciones · {teachers.length} docentes
          </p>
        </div>
        <input
          className="search"
          placeholder="Buscar docente…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="teacher-list">
          {filteredTeachers.map((t) => (
            <button
              key={t.clave}
              className={`teacher-btn${t.clave === teacherKey ? " active" : ""}`}
              onClick={() => {
                setTeacherKey(t.clave);
                setSubject("todas");
              }}
            >
              <span className="name">{t.nombre}</span>
              <span className="meta">
                {t.cargos.join(" · ") || "Sin cargo"} · {t.respuestas} resp. · {t.materias} cátedras
              </span>
            </button>
          ))}
        </div>
      </aside>

      <main className="main">
        {!selectedTeacher ? (
          <div className="empty">
            Elegí un docente a la izquierda para ver las respuestas agrupadas por pregunta.
          </div>
        ) : (
          <>
            <header className="hero">
              <div>
                <h1>{selectedTeacher.nombre}</h1>
                <p>
                  {selectedTeacher.cargos.join(" · ")} · fuente {data.fuente}
                </p>
              </div>
            </header>

            <section className="kpis">
              <div className="kpi">
                <span>Respuestas</span>
                <strong>{visibleRecords.length}</strong>
              </div>
              <div className="kpi">
                <span>Cátedras</span>
                <strong>{subject === "todas" ? selectedTeacher.materias : 1}</strong>
              </div>
              <div className="kpi">
                <span>Preguntas</span>
                <strong>{data.preguntas.length}</strong>
              </div>
            </section>

            <div className="toolbar">
              <select value={subject} onChange={(e) => setSubject(e.target.value)}>
                <option value="todas">Todas las cátedras</option>
                {subjectOptions.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>

            {ejes.map((eje) => (
              <section key={eje}>
                <h2 className="eje">{eje}</h2>
                {data.preguntas
                  .filter((q) => q.eje === eje)
                  .map((q) => {
                    const counts = countAnswers(visibleRecords, q.id);
                    const total = [...counts.values()].reduce((a, b) => a + b, 0);
                    const rows = [...counts.entries()].sort((a, b) => b[1] - a[1]);
                    return (
                      <article key={q.id} className="card question">
                        <h3>{q.short}</h3>
                        <p>{q.text}</p>
                        {rows.length === 0 ? (
                          <p>Sin respuestas en este recorte.</p>
                        ) : (
                          rows.map(([label, n]) => (
                            <div key={label} className="bar-row">
                              <span>{label}</span>
                              <div className="track">
                                <div
                                  className={`fill ${answerTone(label)}`}
                                  style={{ width: `${total ? (n / total) * 100 : 0}%` }}
                                />
                              </div>
                              <span>
                                {n} ({total ? Math.round((n / total) * 100) : 0}%)
                              </span>
                            </div>
                          ))
                        )}
                      </article>
                    );
                  })}
              </section>
            ))}

            <h2 className="eje">Cátedras evaluadas</h2>
            <div className="card" style={{ padding: 16 }}>
              <table className="subjects">
                <thead>
                  <tr>
                    <th>Asignatura / comisión</th>
                    <th>Respuestas</th>
                  </tr>
                </thead>
                <tbody>
                  {subjectRows.map((row) => (
                    <tr key={row.concepto}>
                      <td>{row.concepto}</td>
                      <td>{row.n}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
