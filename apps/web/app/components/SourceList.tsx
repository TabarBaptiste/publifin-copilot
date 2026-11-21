import type { Source } from "@/lib/api";
import styles from "./AskPanel.module.css";

function ExternalIcon() {
  return (
    <svg
      className={styles.externalIcon}
      viewBox="0 0 20 20"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M8 4H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-3" />
      <path d="M11 3h6v6M17 3l-8 8" />
    </svg>
  );
}

function ChevronIcon() {
  return (
    <svg
      className={styles.chevron}
      viewBox="0 0 20 20"
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="m6 8 4 4 4-4" />
    </svg>
  );
}

/** Collapsible list of the cited documents. `scope` keeps anchors unique per answer. */
export function SourceList({
  sources,
  scope,
  open,
}: {
  sources: Source[];
  scope: string;
  open: boolean;
}) {
  return (
    <details className={styles.sources} open={open}>
      <summary className={styles.sourcesSummary}>
        <ChevronIcon />
        {sources.length > 1 ? `${sources.length} sources` : "1 source"}
      </summary>
      <ol className={styles.sourceList}>
        {sources.map((source, index) => {
          const content = (
            <>
              <span className={styles.sourceNumber}>{index + 1}</span>
              <span className={styles.sourceBody}>
                <span className={styles.sourceTitle}>
                  {source.title}, page {source.page}
                </span>
                <span className={styles.sourceExtract}>{source.extract}</span>
              </span>
            </>
          );
          return (
            <li
              key={`${source.source}-${source.page}`}
              id={`${scope}-source-${index + 1}`}
              className={styles.sourceItem}
            >
              {source.url ? (
                <a
                  className={styles.sourceCard}
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {content}
                  <ExternalIcon />
                  <span className={styles.srOnly}>(ouvre le document dans un nouvel onglet)</span>
                </a>
              ) : (
                <div className={styles.sourceCard}>{content}</div>
              )}
            </li>
          );
        })}
      </ol>
    </details>
  );
}
