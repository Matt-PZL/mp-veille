import type { Metadata } from "next";
import InscriptionClient from "./InscriptionClient";

export const metadata: Metadata = { title: "Créer un compte" };

export default function InscriptionPage() {
  return <InscriptionClient />;
}
