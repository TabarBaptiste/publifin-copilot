import type { AnalysisStatus, StepLog } from "@/lib/api";
import styles from "./AnalysisPanel.module.css";

const LABELS: Record<string, string> = {
  extract_request: "Lecture de la demande",
  find_commune: "Identification de la commune (API Géo)",
  get_finances: "Données financières (OFGL)",
  compute_indicators: "Calcul des indicateurs",
  search_rules: "Recherche des règles dans les documents",
  draft_note: "Rédaction de la note",
  human_decision: "Décision humaine",
  save_note: "Enregistrement de la note",
};

// Order in which the agent runs its steps, used to show which one is in progress.
const ORDER = [
  "extract_request",
  "find_commune",
  "get_finances",
  "compute_indicators",
  "search_rules",
  "draft_note",
];

function seconds(ms: number) {
  return ms < 100 ? "< 0,1 s" : `${(ms / 1000).toFixed(1).replace(".", ",")} s`;
}

export function StepTimeline({ steps, status }: { steps: StepLog[]; status: AnalysisStatus }) {
  const done = new Set(steps.map((step) => step.name));
  const current = status === "running" ? ORDER.find((name) => !done.has(name)) : undefined;

  return (
    <ol className={styles.timeline} aria-label="Étapes de l'analyse">
      {steps.map((step) => (
        <li key={step.name} className={styles.stepItem} data-status={step.status}>
          <span className={styles.stepMark} aria-hidden="true">
            {step.status === "ok" ? "✓" : "✕"}
          </span>
          <span className={styles.stepBody}>
            <span className={styles.stepTitle}>
              {LABELS[step.name] ?? step.name}
              <span className={styles.srOnly}>{step.status === "ok" ? " (terminée)" : " (échec)"}</span>
            </span>
            <span className={styles.stepSummary}>{step.summary}</span>
          </span>
          {step.duration_ms > 0 && <span className={styles.stepTime}>{seconds(step.duration_ms)}</span>}
        </li>
      ))}
      {current && (
        <li className={styles.stepItem} data-status="running">
          <span className={styles.spinner} aria-hidden="true" />
          <span className={styles.stepBody}>
            <span className={styles.stepTitle}>
              {LABELS[current]}
              <span className={styles.srOnly}> (en cours)</span>
            </span>
          </span>
        </li>
      )}
    </ol>
  );
}
