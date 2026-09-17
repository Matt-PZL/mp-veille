import type { Metadata } from "next";
import { NavBar } from "@/components/vitrine/NavBar";
import { HeroDetection } from "@/components/vitrine/HeroDetection";
import { SectionProbleme } from "@/components/vitrine/SectionProbleme";
import { SectionSolution } from "@/components/vitrine/SectionSolution";
import { SectionProjection } from "@/components/vitrine/SectionProjection";

/**
 * Site vitrine — racine publique.
 *
 * Distincte du panel applicatif, qui vit sous /app derriere l'authentification.
 */
export const metadata: Metadata = {
  title: "Cyrens — veille cyber sur vos actifs",
  description:
    "La veille cybersécurité corrélée à vos actifs réels : serveurs, logiciels et référentiels de conformité confrontés en continu aux vulnérabilités, avis et échéances qui les concernent.",
};

export default function PageAccueil() {
  return (
    <>
      <NavBar />
      <main>
        <HeroDetection />
        <SectionProbleme />
        <SectionSolution />
        <SectionProjection />
      </main>
    </>
  );
}
