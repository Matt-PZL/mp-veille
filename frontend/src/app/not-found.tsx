import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center px-[18px]">
      <div className="max-w-[420px] text-center">
        <p className="font-mono text-[11px] font-semibold tracking-[0.13em] text-accent uppercase">
          Erreur 404
        </p>
        <h1 className="mt-2 font-display text-[22px] font-extrabold tracking-tight">
          Cette page n&apos;existe pas
        </h1>
        <p className="mt-2 text-[13px] leading-relaxed text-ink-soft">
          Le lien est peut-être obsolète, ou le renseignement a été retiré de la base.
        </p>
        <Link
          href="/"
          className="mt-5 inline-flex items-center rounded-lg border border-accent bg-accent px-[18px] py-2.5 text-[13px] font-semibold text-accent-ink"
        >
          Retour à la vue d&apos;ensemble
        </Link>
      </div>
    </div>
  );
}
