"use client";

import {
  type FormEvent,
  type KeyboardEvent,
  type ReactNode,
  useEffect,
  useRef,
  useState,
} from "react";
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

/** One exchange of the thread. Each question is independent: the API keeps no history. */
type Turn = { id: number; question: string } & (
  | { status: "loading" }
  | { status: "done"; result: AskResult }
  | { status: "error"; message: string }
);

function Icon({ children }: { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 20 20"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

/** Mounted only while a question is running, so its timer restarts for every question. */
function LoadingStatus() {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setElapsed((seconds) => seconds + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className={styles.status} role="status">
      <p>
        <span className={styles.shimmer}>Recherche dans les documents…</span>{" "}
        <span className={styles.elapsed}>{elapsed} s</span>
      </p>
      {elapsed >= 8 && (
        <p className={styles.hint}>
          Le modèle tourne en local : une réponse peut prendre jusqu&apos;à une minute.
        </p>
      )}
    </div>
  );
}

export function AskPanel() {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const controller = useRef<AbortController | null>(null);
  const nextId = useRef(1);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const lastTurn = useRef<HTMLElement>(null);

  const loading = turns.at(-1)?.status === "loading";
  const canSubmit = question.trim().length >= MIN_LENGTH && !loading;

  // Grow the field with its content (up to a cap), shrink it back once it is emptied.
  useEffect(() => {
    const field = textarea.current;
    if (!field) return;
    field.style.height = "auto";
    field.style.height = `${Math.min(field.scrollHeight, 200)}px`;
  }, [question]);

  // Bring a new exchange into view; the sticky composer is accounted for by scroll-margin.
  useEffect(() => {
    if (turns.length === 0) return;
    const smooth = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    lastTurn.current?.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "start" });
  }, [turns.length]);

  function update(id: number, next: Turn) {
    setTurns((current) => current.map((turn) => (turn.id === id ? next : turn)));
  }

  async function run(id: number, text: string) {
    // Forget a previous "#…-source-n" so a new answer does not start with a highlighted card.
    if (window.location.hash) window.history.replaceState(null, "", window.location.pathname);
    controller.current = new AbortController();
    try {
      const result = await ask(text, controller.current.signal);
      update(id, { id, question: text, status: "done", result });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      const message =
        error instanceof ApiError ? error.message : "Une erreur inattendue est survenue.";
      update(id, { id, question: text, status: "error", message });
    }
  }

  function submit(text: string) {
    const trimmed = text.trim();
    if (trimmed.length < MIN_LENGTH || loading) return;
    const id = nextId.current++;
    setTurns((current) => [...current, { id, question: trimmed, status: "loading" }]);
    setQuestion("");
    void run(id, trimmed);
  }

  function retry(turn: Turn) {
    update(turn.id, { id: turn.id, question: turn.question, status: "loading" });
    void run(turn.id, turn.question);
  }

  /** Stop the running question and give it back to the field so it can be edited. */
  function stop() {
    controller.current?.abort();
    const running = turns.at(-1);
    if (running?.status !== "loading") return;
    setTurns((current) => current.filter((turn) => turn.id !== running.id));
    setQuestion(running.question);
    textarea.current?.focus();
  }

  function reset() {
    controller.current?.abort();
    setTurns([]);
    setQuestion("");
    textarea.current?.focus();
  }

  async function copy(turn: Turn & { status: "done" }) {
    try {
      await navigator.clipboard.writeText(turn.result.answer);
      setCopiedId(turn.id);
      setTimeout(() => setCopiedId((current) => (current === turn.id ? null : current)), 2000);
    } catch {
      // Clipboard can be blocked (insecure context, permissions): the button just does nothing.
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (loading) stop();
    else submit(question);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends, Shift+Enter adds a line; ignore the Enter that validates an IME composition.
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit(question);
    }
  }

  return (
    <div className={styles.panel}>
      {turns.length === 0 ? (
        <section aria-labelledby="examples-title" className={styles.examples}>
          <h2 id="examples-title" className={styles.sectionTitle}>
            Exemples de questions
          </h2>
          <ul className={styles.chips}>
            {EXAMPLES.map((example) => (
              <li key={example}>
                <button type="button" className={styles.chip} onClick={() => submit(example)}>
                  {example}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <div className={styles.thread} role="log" aria-live="polite" aria-label="Conversation">
          {turns.map((turn, index) => {
            const isLast = index === turns.length - 1;
            const scope = `t${turn.id}`;
            return (
              <article key={turn.id} ref={isLast ? lastTurn : undefined} className={styles.turn}>
                <p className={styles.userMessage}>{turn.question}</p>

                <div className={styles.reply}>
                  {turn.status === "loading" && <LoadingStatus />}

                  {turn.status === "error" && (
                    <div className={styles.error} role="alert">
                      <h2 className={styles.sectionTitle}>Réponse impossible</h2>
                      <p>{turn.message}</p>
                      <button type="button" className={styles.secondary} onClick={() => retry(turn)}>
                        Réessayer
                      </button>
                    </div>
                  )}

                  {turn.status === "done" && turn.result.refused && (
                    <div className={styles.notice}>
                      <h2 className={styles.sectionTitle}>Aucune réponse dans les documents</h2>
                      <p>{turn.result.answer}</p>
                      <p className={styles.hint}>
                        Reformulez avec les termes d&apos;un texte (article, seuil, notion) ou posez
                        une question sur le RGPD, l&apos;AI Act, les recommandations de la CNIL ou
                        les finances locales.
                      </p>
                    </div>
                  )}

                  {turn.status === "done" && !turn.result.refused && (
                    <>
                      <AnswerText
                        text={turn.result.answer}
                        sources={turn.result.sources}
                        scope={scope}
                      />
                      <div className={styles.actions}>
                        <button
                          type="button"
                          className={styles.ghost}
                          onClick={() => void copy(turn)}
                        >
                          <Icon>
                            <rect x="7" y="7" width="9" height="9" rx="1.5" />
                            <path d="M13 7V5.5A1.5 1.5 0 0 0 11.5 4h-6A1.5 1.5 0 0 0 4 5.5v6A1.5 1.5 0 0 0 5.5 13H7" />
                          </Icon>
                          {copiedId === turn.id ? "Copié" : "Copier la réponse"}
                        </button>
                      </div>
                      {turn.result.sources.length > 0 && (
                        <SourceList
                          sources={turn.result.sources}
                          scope={scope}
                          open={isLast}
                        />
                      )}
                    </>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}

      <div className={styles.composer}>
        <form onSubmit={onSubmit} className={styles.form}>
          <label htmlFor="question" className={styles.srOnly}>
            Votre question
          </label>
          <textarea
            id="question"
            ref={textarea}
            className={styles.textarea}
            rows={1}
            maxLength={MAX_LENGTH}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={onKeyDown}
            aria-describedby="question-hint"
            placeholder="Posez votre question…"
          />
          {loading ? (
            <button type="submit" className={styles.send} aria-label="Arrêter la recherche">
              <Icon>
                <rect x="5.5" y="5.5" width="9" height="9" rx="1.5" fill="currentColor" />
              </Icon>
            </button>
          ) : (
            <button
              type="submit"
              className={styles.send}
              disabled={!canSubmit}
              aria-label="Envoyer la question"
            >
              <Icon>
                <path d="M10 16V4M5 9l5-5 5 5" />
              </Icon>
            </button>
          )}
        </form>
        <div className={styles.composerMeta}>
          <p id="question-hint" className={`${styles.hint} ${styles.keyHint}`}>
            Entrée pour envoyer, Maj + Entrée pour un retour à la ligne
            {question.length > MAX_LENGTH * 0.8 && ` · ${question.length}/${MAX_LENGTH}`}
          </p>
          {turns.length > 0 && (
            <button type="button" className={styles.ghost} onClick={reset}>
              <Icon>
                <path d="M10 4v12M4 10h12" />
              </Icon>
              Nouvelle conversation
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
