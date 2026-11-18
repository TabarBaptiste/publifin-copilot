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
