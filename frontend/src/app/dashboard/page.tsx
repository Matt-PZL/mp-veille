import type { Metadata } from "next";
import DashboardClient from "./DashboardClient";

export const metadata: Metadata = { title: "Vue d'ensemble" };

export default function DashboardPage() {
  return <DashboardClient />;
}
