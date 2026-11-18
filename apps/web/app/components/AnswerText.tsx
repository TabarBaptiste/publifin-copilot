import styles from "./AskPanel.module.css";

/** Renders the answer text, turning "[n]" markers into links to the matching source card. */
export function AnswerText({ text }: { text: string }) {
  const parts = text.split(/\[(\d+)\]/);
  return (
    <p className={styles.answerText}>
      {parts.map((part, index) =>
        index % 2 === 1 ? (
          <a
            key={index}
            href={`#source-${part}`}
            className={styles.cite}
            aria-label={`Voir la source ${part}`}
          >
            {part}
          </a>
        ) : (
          part
        ),
      )}
    </p>
  );
}
