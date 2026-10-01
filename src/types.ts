export type Question = {
  id: string;
  eje: string;
  short: string;
  text: string;
};

export type SurveyRecord = {
  id: string;
  docente: string;
  docenteClave: string;
  cargo: string;
  concepto: string;
  materia: string;
  codigoMateria: string;
  comision: string;
  fechaInicio: string | null;
  fechaFin: string | null;
  respuestas: Record<string, string>;
  puntajes: Record<string, number>;
};

export type SurveyData = {
  fuente: string;
  periodo: string;
  preguntas: Question[];
  registros: SurveyRecord[];
};

export type TeacherSummary = {
  clave: string;
  nombre: string;
  cargos: string[];
  respuestas: number;
  materias: number;
  promedio: number | null;
};
