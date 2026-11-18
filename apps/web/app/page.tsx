import { AskPanel } from "./components/AskPanel";
import { Shell } from "./components/Shell";

export default function Home() {
  return (
    <Shell
      title="PubliFin Copilot"
      subtitle="Posez une question sur le RGPD, l'AI Act, les recommandations de la CNIL ou les finances des collectivités. Chaque réponse cite ses sources."
    >
      <AskPanel />
    </Shell>
  );
}
