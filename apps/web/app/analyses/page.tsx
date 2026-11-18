import type { Metadata } from "next";
import { AnalysisPanel } from "../components/AnalysisPanel";
import { Shell } from "../components/Shell";

export const metadata: Metadata = { title: "Pré-analyse · PubliFin Copilot" };

export default function AnalysesPage() {
  return (
    <Shell
      title="Pré-analyse d'une demande de financement"
      subtitle="Décrivez la demande d'une commune. L'agent rassemble les données publiques et les règles applicables, rédige une note, puis attend votre validation avant tout enregistrement."
    >
      <AnalysisPanel />
    </Shell>
  );
}
