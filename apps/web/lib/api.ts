const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Source = {
  source: string;
  title: string;
  page: number;
  extract: string;
  url: string | null;
};

export type AskResult = {
  answer: string;
  sources: Source[];
  refused: boolean;
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly kind: "unavailable" | "unreachable" | "invalid",
  ) {
    super(message);
  }
}

export async function ask(question: string, signal: AbortSignal): Promise<AskResult> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(`Impossible de joindre l'API (${API_URL}).`, "unreachable");
  }

  if (response.status === 503) {
    throw new ApiError(
      "Le modèle de langage ne répond pas. Vérifiez qu'Ollama est lancé, puis réessayez.",
      "unavailable",
    );
  }
  if (!response.ok) {
    throw new ApiError("La question n'a pas pu être traitée.", "invalid");
  }
  return response.json();
}

// ---- Pre-analysis agent ----

export type AnalysisStatus = "running" | "awaiting_review" | "approved" | "rejected" | "failed";

export type StepLog = {
  name: string;
  status: "ok" | "error";
  duration_ms: number;
  summary: string;
};

export type Analysis = {
  id: string;
  status: AnalysisStatus;
  request: string;
  steps: StepLog[];
  draft_note: string | null;
  rules: Source[];
  error: string | null;
};

export type AuditItem = {
  kind: string;
  name: string;
  status: string;
  actor: string;
  duration_ms: number | null;
};

export type Decision = {
  action: "approve" | "edit" | "reject";
  reviewer: string;
  note?: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    throw new ApiError(`Impossible de joindre l'API (${API_URL}).`, "unreachable");
  }
  if (response.status === 503) {
    throw new ApiError(
      "Le service d'analyse est indisponible (base de données ou modèle arrêtés).",
      "unavailable",
    );
  }
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new ApiError(
      typeof detail?.detail === "string" ? detail.detail : "La requête a été refusée.",
      "invalid",
    );
  }
  return response.json();
}

export async function startAnalysis(text: string): Promise<string> {
  const { id } = await request<{ id: string }>("/analyses", {
    method: "POST",
    body: JSON.stringify({ request: text }),
  });
  return id;
}

export const getAnalysis = (id: string) => request<Analysis>(`/analyses/${id}`);

export const decideAnalysis = (id: string, decision: Decision) =>
  request<Analysis>(`/analyses/${id}/decision`, {
    method: "POST",
    body: JSON.stringify(decision),
  });

export const getAudit = (id: string) => request<AuditItem[]>(`/analyses/${id}/audit`);
