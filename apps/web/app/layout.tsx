import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

const geist = Geist({
  variable: "--font-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PubliFin Copilot",
  description:
    "Assistant documentaire pour chargés d'affaires : questions sur le RGPD, l'AI Act, la CNIL et les finances locales, avec sources citées.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="fr" className={geist.variable}>
      <body>{children}</body>
    </html>
  );
}
