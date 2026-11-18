"use client";

import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";
import { ApiError, ask, type AskResult } from "@/lib/api";
import { AnswerText } from "./AnswerText";
import { SourceList } from "./SourceList";
import styles from "./AskPanel.module.css";

const MAX_LENGTH = 1000;
const MIN_LENGTH = 3;

const EXAMPLES = [
  "Dans quel délai faut-il notifier une violation de données personnelles ?",
  "Quel est le seuil d'alerte de l'épargne brute des communes ?",
  "Quelles pratiques d'IA sont interdites par l'AI Act ?",
];

type State =
  | { status: "idle" }
  | { status: "loading"; question: string }
  | { status: "done"; question: string; result: AskResult }
  | { status: "error"; question: string; message: string };

/** Mounted only while a question is running, so its timer restarts for every question. */
function LoadingStatus({ onCancel }: { onCancel: () => void }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setElapsed((seconds) => seconds + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className={styles.status} role="status">
      <span className={styles.spinner} aria-hidden="true" />
      <div>
        <p>Recherche dans les documents… {elapsed} s</p>
        {elapsed >= 8 && (
          <p className={styles.hint}>
            Le modèle tourne en local : une réponse peut prendre jusqu&apos;à une minute.
          </p>
        )}
      </div>
      <button type="button" className={styles.secondary} onClick={onCancel}>
        Annuler
      </button>
    </div>
  );
}

export function AskPanel() {
  const [question, setQuestion] = useState("");
  const [state, setState] = useState<State>({ status: "idle" });
  const controller = useRef<AbortController | null>(null);

  const loading = state.status === "loading";
  const canSubmit = question.trim().length >= MIN_LENGTH && !loading;

  async function submit(text: string) {
    const trimmed = text.trim();
    if (trimmed.length < MIN_LENGTH) return;
    // Forget a previous "#source-n" so a new answer does not start with a highlighted card.
    if (window.location.hash) window.history.replaceState(null, "", window.location.pathname);
    controller.current?.abort();
    controller.current = new AbortController();
    setState({ status: "loading", question: trimmed });
    try {
      const result = await ask(trimmed, controller.current.signal);
      setState({ status: "done", question: trimmed, result });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      const message =
        error instanceof ApiError ? error.message : "Une erreur inattendue est survenue.";
      setState({ status: "error", question: trimmed, message });
    }
  }

  function cancel() {
    controller.current?.abort();
    setState({ status: "idle" });
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void submit(question);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void submit(question);
    }
  }

  function askExample(text: string) {
    setQuestion(text);
    void submit(text);
  }

  return (
    <div className={styles.panel}>
      <form onSubmit={onSubmit} className={styles.form}>
        <label htmlFor="question" className={styles.label}>
          Votre question
        </label>
        <textarea
          id="question"
          className={styles.textarea}
          rows={3}
          maxLength={MAX_LENGTH}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={onKeyDown}
          aria-describedby="question-hint"
          placeholder="Ex. : Quel est le plafond d'amende prévu par le RGPD ?"
        />
        <div className={styles.row}>
          <p id="question-hint" className={styles.hint}>
            Ctrl + Entrée pour envoyer · {question.length}/{MAX_LENGTH}
          </p>
          <button type="submit" className={styles.primary} disabled={!canSubmit}>
            Poser la question
          </button>
        </div>
      </form>

      {state.status === "idle" && (
        <section aria-labelledby="examples-title" className={styles.examples}>
          <h2 id="examples-title" className={styles.sectionTitle}>
            Exemples de questions
          </h2>
          <ul className={styles.chips}>
            {EXAMPLES.map((example) => (
              <li key={example}>
                <button type="button" className={styles.chip} onClick={() => askExample(example)}>
                  {example}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div aria-live="polite" className={styles.results}>
        {state.status === "loading" && <LoadingStatus onCancel={cancel} />}

        {state.status === "error" && (
          <div className={styles.error} role="alert">
            <h2 className={styles.sectionTitle}>Réponse impossible</h2>
            <p>{state.message}</p>
            <button
              type="button"
              className={styles.secondary}
              onClick={() => void submit(state.question)}
            >
              Réessayer
            </button>
          </div>
        )}

        {state.status === "done" && state.result.refused && (
          <div className={styles.notice}>
            <h2 className={styles.sectionTitle}>Aucune réponse dans les documents</h2>
            <p>{state.result.answer}</p>
            <p className={styles.hint}>
              Reformulez avec les termes d&apos;un texte (article, seuil, notion) ou posez une
              question sur le RGPD, l&apos;AI Act, les recommandations de la CNIL ou les finances
              locales.
            </p>
          </div>
        )}

        {state.status === "done" && !state.result.refused && (
          <>
            <section aria-labelledby="answer-title" className={styles.answer}>
              <h2 id="answer-title" className={styles.sectionTitle}>
                Réponse
              </h2>
              <AnswerText text={state.result.answer} />
            </section>
            <SourceList sources={state.result.sources} />
          </>
        )}
      </div>
    </div>
  );
}
