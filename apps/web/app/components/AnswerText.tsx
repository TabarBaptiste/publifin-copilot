import type { Source } from "@/lib/api";
import styles from "./AskPanel.module.css";

/**
 * Renders the answer text, turning "[n]" markers into citations: a link to the matching source
 * card, with a hover card (title, page, extract) on devices that can hover.
 * `scope` keeps the anchors unique when several answers are on the page.
 */
export function AnswerText({
  text,
  sources,
  scope,
}: {
  text: string;
  sources: Source[];
  scope: string;
}) {
  const parts = text.split(/\[(\d+)\]/);
  return (
    <p className={styles.answerText}>
      {parts.map((part, index) => {
        if (index % 2 === 0) return part;
        const source = sources[Number(part) - 1];
        // A marker without a matching source stays plain text instead of a dead link.
        if (!source) return `[${part}]`;
        return (
          <span key={index} className={styles.citeWrap}>
            <a
              href={`#${scope}-source-${part}`}
              className={styles.cite}
              aria-label={`Voir la source ${part}`}
            >
              {part}
            </a>
            <span className={styles.citeCard} aria-hidden="true">
              <span className={styles.citeTitle}>
                {source.title}, page {source.page}
              </span>
              <span className={styles.citeExtract}>{source.extract}</span>
            </span>
          </span>
        );
      })}
    </p>
  );
}
