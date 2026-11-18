import { AskPanel } from "./components/AskPanel";
import styles from "./page.module.css";

export default function Home() {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>PubliFin Copilot</h1>
        <p className={styles.subtitle}>
          Posez une question sur le RGPD, l&apos;AI Act, les recommandations de la CNIL ou les
          finances des collectivités. Chaque réponse cite ses sources.
        </p>
      </header>
      <main>
        <AskPanel />
      </main>
      <footer className={styles.footer}>
        <p>
          Réponses générées à partir de documents publics par un modèle d&apos;IA. Vérifiez les
          sources avant toute décision.
        </p>
      </footer>
    </div>
  );
}
