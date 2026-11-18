"use client";

import { type FormEvent, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  ApiError,
  type Analysis,
  type AuditItem,
  decideAnalysis,
  getAnalysis,
  getAudit,
  startAnalysis,
} from "@/lib/api";
import { StepTimeline } from "./StepTimeline";
import styles from "./AnalysisPanel.module.css";

const MIN_LENGTH = 10;
const MAX_LENGTH = 1000;

const EXAMPLES = [
  "La commune de Quimper demande 2 M€ pour rénover son école.",
  "La commune de Bastia demande 40 M€ pour rénover son port de plaisance.",
];

function errorMessage(error: unknown) {
  return error instanceof ApiError ? error.message : "Une erreur inattendue est survenue.";
}

export function AnalysisPanel() {
  const [text, setText] = useState("");
  const [id, setId] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const status = analysis?.status;
  const active = id !== null && (status === undefined || status === "running");
  const canStart = text.trim().length >= MIN_LENGTH && !busy && !active;

  // Poll the analysis while the agent works; stop at the review or at the end.
  useEffect(() => {
    if (!id || (status !== undefined && status !== "running")) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const next = await getAnalysis(id);
        if (!cancelled) setAnalysis(next);
      } catch (cause) {
        if (!cancelled) setError(errorMessage(cause));
      }
    };
    const timer = setInterval(tick, 1500);
    void tick();
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [id, status]);

  async function start(request: string) {
    if (request.trim().length < MIN_LENGTH) return;
    setBusy(true);
    setError(null);
    setAnalysis(null);
    setId(null);
    try {
      setId(await startAnalysis(request.trim()));
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void start(text);
  }

  function askExample(example: string) {
    setText(example);
    void start(example);
  }

  return (
    <div className={styles.panel}>
      <form onSubmit={onSubmit} className={styles.form}>
        <label htmlFor="request" className={styles.label}>
          Demande de financement
        </label>
        <textarea
          id="request"
          className={styles.textarea}
          rows={3}
          maxLength={MAX_LENGTH}
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Ex. : La commune de Quimper demande 2 M€ pour rénover son école."
        />
        <div className={styles.row}>
          <p className={styles.hint}>
            {text.length}/{MAX_LENGTH}
          </p>
          <button type="submit" className={styles.primary} disabled={!canStart}>
            Lancer la pré-analyse
          </button>
        </div>
      </form>

      {!id && !error && (
        <section aria-labelledby="examples-title" className={styles.section}>
          <h2 id="examples-title" className={styles.sectionTitle}>
            Exemples de demandes
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
        {error && (
          <div className={styles.error} role="alert">
            <h2 className={styles.sectionTitle}>Analyse impossible</h2>
            <p>{error}</p>
          </div>
        )}

        {id && !analysis && !error && (
          <p className={styles.hint} role="status">
            Démarrage de l&apos;analyse…
          </p>
        )}

        {analysis && (
          <>
            <section aria-labelledby="steps-title" className={styles.section}>
              <h2 id="steps-title" className={styles.sectionTitle}>
                Étapes
              </h2>
              <StepTimeline steps={analysis.steps} status={analysis.status} />
            </section>

            {analysis.status === "failed" && (
              <div className={styles.error} role="alert">
                <h2 className={styles.sectionTitle}>L&apos;analyse s&apos;est arrêtée</h2>
                <p>{analysis.error}</p>
                <p className={styles.hint}>Rien n&apos;a été enregistré.</p>
              </div>
            )}

            {analysis.status === "awaiting_review" && analysis.draft_note && (
              <Review analysis={analysis} onDone={setAnalysis} onError={setError} />
            )}

            {analysis.status === "approved" && (
              <div className={styles.notice}>
                <h2 className={styles.sectionTitle}>Note enregistrée</h2>
                <p>La note a été validée et enregistrée. La décision figure dans le journal d&apos;audit.</p>
              </div>
            )}

            {analysis.status === "rejected" && (
              <div className={styles.notice}>
                <h2 className={styles.sectionTitle}>Note rejetée</h2>
                <p>Rien n&apos;a été enregistré. Le rejet figure dans le journal d&apos;audit.</p>
              </div>
            )}

            {["approved", "rejected", "failed"].includes(analysis.status) && (
              <AuditTrail id={analysis.id} />
            )}
          </>
        )}
      </div>
    </div>
  );
}

function Review({
  analysis,
  onDone,
  onError,
}: {
  analysis: Analysis;
  onDone: (analysis: Analysis) => void;
  onError: (message: string) => void;
}) {
  const [reviewer, setReviewer] = useState("");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(analysis.draft_note ?? "");
  const [sending, setSending] = useState(false);
  const ready = reviewer.trim().length >= 2 && !sending && (!editing || draft.trim().length > 0);

  async function send(action: "approve" | "edit" | "reject") {
    setSending(true);
    try {
      const result = await decideAnalysis(analysis.id, {
        action,
        reviewer: reviewer.trim(),
        note: action === "edit" ? draft : undefined,
      });
      onDone(result);
    } catch (cause) {
      onError(errorMessage(cause));
      setSending(false);
    }
  }

  return (
    <section aria-labelledby="review-title" className={styles.review}>
      <h2 id="review-title" className={styles.sectionTitle}>
        Note à valider
      </h2>
      <p className={styles.hint}>
        Rien n&apos;est enregistré tant que vous n&apos;avez pas validé. Relisez les chiffres et les
        sources.
      </p>

      {editing ? (
        <>
          <label htmlFor="note-edit" className={styles.label}>
            Note (Markdown)
          </label>
          <textarea
            id="note-edit"
            className={styles.textarea}
            rows={18}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
        </>
      ) : (
        <div className={styles.note}>
          <ReactMarkdown>{analysis.draft_note}</ReactMarkdown>
        </div>
      )}

      {analysis.rules.length > 0 && (
        <div>
          <h3 className={styles.subTitle}>Documents consultés</h3>
          <ul className={styles.links}>
            {analysis.rules.map((rule) => (
              <li key={`${rule.source}-${rule.page}`}>
                {rule.url ? (
                  <a href={rule.url} target="_blank" rel="noopener noreferrer">
                    {rule.title}, page {rule.page}
                    <span className={styles.srOnly}> (ouvre le document dans un nouvel onglet)</span>
                  </a>
                ) : (
                  `${rule.title}, page ${rule.page}`
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className={styles.reviewer}>
        <label htmlFor="reviewer" className={styles.label}>
          Votre nom
        </label>
        <input
          id="reviewer"
          className={styles.input}
          value={reviewer}
          maxLength={100}
          autoComplete="name"
          onChange={(event) => setReviewer(event.target.value)}
        />
        <p className={styles.hint}>Il est inscrit dans le journal d&apos;audit avec votre décision.</p>
      </div>

      <div className={styles.actions}>
        <button
          type="button"
          className={styles.primary}
          disabled={!ready}
          onClick={() => void send(editing ? "edit" : "approve")}
        >
          {editing ? "Enregistrer la note corrigée" : "Valider la note"}
        </button>
        <button type="button" className={styles.secondary} disabled={sending} onClick={() => setEditing(!editing)}>
          {editing ? "Annuler la modification" : "Modifier la note"}
        </button>
        <button
          type="button"
          className={styles.secondary}
          disabled={reviewer.trim().length < 2 || sending}
          onClick={() => void send("reject")}
        >
          Rejeter
        </button>
      </div>
    </section>
  );
}

function AuditTrail({ id }: { id: string }) {
  const [items, setItems] = useState<AuditItem[] | null>(null);
  const [failed, setFailed] = useState(false);

  async function load() {
    if (items) return;
    try {
      setItems(await getAudit(id));
    } catch {
      setFailed(true);
    }
  }

  return (
    <details className={styles.audit} onToggle={(event) => event.currentTarget.open && void load()}>
      <summary>Journal d&apos;audit</summary>
      {failed && <p>Le journal n&apos;a pas pu être chargé.</p>}
      {items && (
        <ul className={styles.auditList}>
          {items.map((item, index) => (
            <li key={index}>
              <strong>{item.name}</strong> · {item.kind === "human_decision" ? `décision de ${item.actor}` : item.kind}
              {item.duration_ms ? ` · ${(item.duration_ms / 1000).toFixed(1).replace(".", ",")} s` : ""}
              {item.status === "error" ? " · échec" : ""}
            </li>
          ))}
        </ul>
      )}
    </details>
  );
}
