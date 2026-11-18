import type { ReactNode } from "react";
import { SiteNav } from "./SiteNav";
import styles from "./Shell.module.css";

export function Shell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className={styles.page}>
      <SiteNav />
      <header className={styles.header}>
        <h1 className={styles.title}>{title}</h1>
        <p className={styles.subtitle}>{subtitle}</p>
      </header>
      <main>{children}</main>
      <footer className={styles.footer}>
        <p>
          Réponses générées à partir de documents et de données publiques par un modèle d&apos;IA.
          Vérifiez les sources avant toute décision.
        </p>
      </footer>
    </div>
  );
}
