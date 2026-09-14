"use client";

/**
 * Frontiere d'erreur de dernier recours.
 *
 * Elle se rend en dehors du layout racine : elle ne peut donc utiliser aucun
 * contexte de l'application (theme, session) et doit porter ses propres
 * <html> et <body>, avec des couleurs ecrites en dur.
 */

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="fr">
      <body
        style={{
          background: "#0a0a0b",
          color: "#f2f3f5",
          fontFamily: "system-ui, -apple-system, sans-serif",
          display: "flex",
          minHeight: "100vh",
          alignItems: "center",
          justifyContent: "center",
          margin: 0,
          padding: 24,
        }}
      >
        <div style={{ maxWidth: 420, textAlign: "center" }}>
          <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
            Une erreur inattendue est survenue
          </h1>
          <p style={{ fontSize: 14, lineHeight: 1.6, color: "#9a9ea8", marginBottom: 20 }}>
            L&apos;application n&apos;a pas pu afficher cette page.
            {error.digest && (
              <>
                <br />
                <code style={{ fontSize: 12 }}>Référence : {error.digest}</code>
              </>
            )}
          </p>
          <button
            onClick={reset}
            style={{
              background: "#3b7bff",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              padding: "9px 18px",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Réessayer
          </button>
        </div>
      </body>
    </html>
  );
}
