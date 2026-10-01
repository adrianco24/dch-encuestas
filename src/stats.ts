import type { SurveyRecord, TeacherSummary } from "./types";

const TONE: Record<string, string> = {
  "muy buena": "excelente",
  "en general si": "excelente",
  "estrictamente": "excelente",
  buena: "buena",
  medianamente: "buena",
  regular: "regular",
  poco: "regular",
  deficiente: "deficiente",
  no: "deficiente",
  "no opina": "sin-opinion",
};

export function answerKey(label: string): string {
  return label
    .toLowerCase()
    .replaceAll("sí", "si")
    .replace(/\s+/g, " ")
    .trim();
}

export function answerTone(label: string): string {
  return TONE[answerKey(label)] ?? "neutro";
}

export function mean(values: number[]): number | null {
  if (!values.length) return null;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

export function teachersFrom(records: SurveyRecord[]): TeacherSummary[] {
  const map = new Map<
    string,
    { nombre: string; cargos: Set<string>; n: number; materias: Set<string>; scores: number[] }
  >();

  for (const rec of records) {
    let entry = map.get(rec.docenteClave);
    if (!entry) {
      entry = {
        nombre: rec.docente,
        cargos: new Set(),
        n: 0,
        materias: new Set(),
        scores: [],
      };
      map.set(rec.docenteClave, entry);
    }
    entry.n += 1;
    if (rec.cargo) entry.cargos.add(rec.cargo);
    entry.materias.add(rec.concepto);
    const scores = Object.values(rec.puntajes);
    const avg = mean(scores);
    if (avg != null) entry.scores.push(avg);
  }

  return [...map.entries()]
    .map(([clave, e]) => ({
      clave,
      nombre: e.nombre,
      cargos: [...e.cargos],
      respuestas: e.n,
      materias: e.materias.size,
      promedio: mean(e.scores),
    }))
    .sort((a, b) => a.nombre.localeCompare(b.nombre, "es"));
}

export function countAnswers(records: SurveyRecord[], questionId: string): Map<string, number> {
  const counts = new Map<string, number>();
  for (const rec of records) {
    const label = rec.respuestas[questionId];
    if (!label) continue;
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }
  return counts;
}

export function subjectsOf(records: SurveyRecord[]): { concepto: string; n: number; promedio: number | null }[] {
  const map = new Map<string, { n: number; scores: number[] }>();
  for (const rec of records) {
    let entry = map.get(rec.concepto);
    if (!entry) {
      entry = { n: 0, scores: [] };
      map.set(rec.concepto, entry);
    }
    entry.n += 1;
    const avg = mean(Object.values(rec.puntajes));
    if (avg != null) entry.scores.push(avg);
  }
  return [...map.entries()]
    .map(([concepto, e]) => ({ concepto, n: e.n, promedio: mean(e.scores) }))
    .sort((a, b) => b.n - a.n);
}

export function formatScore(value: number | null): string {
  if (value == null) return "—";
  return value.toFixed(2);
}
