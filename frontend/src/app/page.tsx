"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import "./landing.css";

const Check = () => (
  <svg viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5" /></svg>
);

export default function LandingPage() {
  const rootRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [navScrolled, setNavScrolled] = useState(false);
  const [contactState, setContactState] = useState<"idle" | "envoi" | "ok" | "erreur">("idle");

  // ---- Reveal au scroll + nav figee ----
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const reveals = root.querySelectorAll(".reveal");
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    reveals.forEach((el) => io.observe(el));

    const onScroll = () => setNavScrolled(window.scrollY > 12);
    onScroll();
    document.addEventListener("scroll", onScroll, { passive: true });

    // Compteurs animes
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const ioCount = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (!e.isIntersecting) return;
          const el = e.target as HTMLElement;
          const cible = parseInt(el.dataset.count || "0", 10);
          if (reduced) {
            el.textContent = String(cible);
          } else {
            const duree = 1200;
            const debut = performance.now();
            const tick = (now: number) => {
              const p = Math.min(1, (now - debut) / duree);
              const ease = 1 - Math.pow(1 - p, 3);
              el.textContent = String(Math.round(cible * ease));
              if (p < 1) requestAnimationFrame(tick);
            };
            requestAnimationFrame(tick);
          }
          ioCount.unobserve(el);
        });
      },
      { threshold: 0.5 }
    );
    root.querySelectorAll<HTMLElement>(".chiffre .n").forEach((el) => ioCount.observe(el));

    return () => {
      io.disconnect();
      ioCount.disconnect();
      document.removeEventListener("scroll", onScroll);
    };
  }, []);

  // ---- Fond anime : reseau de points relies ----
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let w = 0, h = 0, points: { x: number; y: number; vx: number; vy: number }[] = [];
    let raf = 0;

    function taille() {
      const rect = canvas!.parentElement!.getBoundingClientRect();
      w = canvas!.width = rect.width;
      h = canvas!.height = rect.height;
    }
    function initPoints() {
      const n = Math.max(18, Math.min(46, Math.floor((w * h) / 32000)));
      points = Array.from({ length: n }, () => ({
        x: Math.random() * w, y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.25, vy: (Math.random() - 0.5) * 0.25,
      }));
    }
    function frame() {
      ctx!.clearRect(0, 0, w, h);
      for (const p of points) {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > w) p.vx *= -1;
        if (p.y < 0 || p.y > h) p.vy *= -1;
      }
      for (let i = 0; i < points.length; i++) {
        for (let j = i + 1; j < points.length; j++) {
          const dx = points[i].x - points[j].x, dy = points[i].y - points[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 140) {
            ctx!.strokeStyle = `rgba(29,78,216,${0.22 * (1 - dist / 140)})`;
            ctx!.lineWidth = 1;
            ctx!.beginPath(); ctx!.moveTo(points[i].x, points[i].y); ctx!.lineTo(points[j].x, points[j].y); ctx!.stroke();
          }
        }
      }
      ctx!.fillStyle = "rgba(29,78,216,0.55)";
      for (const p of points) { ctx!.beginPath(); ctx!.arc(p.x, p.y, 1.6, 0, Math.PI * 2); ctx!.fill(); }
      if (!reduced) raf = requestAnimationFrame(frame);
    }
    taille(); initPoints();
    const onResize = () => { taille(); initPoints(); };
    window.addEventListener("resize", onResize);
    frame();
    return () => { window.removeEventListener("resize", onResize); cancelAnimationFrame(raf); };
  }, []);

  const soumettreContact = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);
    setContactState("envoi");
    try {
      await api.contact({
        nom: String(data.get("nom") || ""),
        email: String(data.get("email") || ""),
        entreprise: String(data.get("entreprise") || ""),
        message: String(data.get("message") || ""),
      });
      setContactState("ok");
      form.reset();
    } catch {
      setContactState("erreur");
    }
  };

  return (
    <div className="landingPage" ref={rootRef}>
      <nav className={`nav${navScrolled ? " scrolled" : ""}`}>
        <div className="wrap navInner">
          <Link href="/" className="brand"><span className="sq">V</span>veille</Link>
          <div className="navLinks">
            <a href="#probleme">Problématique</a>
            <a href="#solution">Solution</a>
            <a href="#fonctionnalites">Fonctionnalités</a>
            <a href="#tarifs">Tarifs</a>
            <a href="#contact">Contact</a>
          </div>
          <div className="navActions">
            <Link href="/login" className="btn">Connexion</Link>
            <Link href="/inscription" className="btn btn-primary">Créer un compte</Link>
          </div>
        </div>
      </nav>

      <header className="hero">
        <canvas className="heroCanvas" ref={canvasRef} />
        <div className="wrap heroGrid">
          <div className="heroContent reveal">
            <span className="eyebrow"><span className="eyebrowDot" />Connecté en direct à NVD · CERT-FR · CNIL</span>
            <h1>Ne laissez plus une <span className="hl">vulnérabilité critique</span> se perdre dans le bruit.</h1>
            <p className="lead">Veille centralise le renseignement cyber et normatif, le met en correspondance avec les actifs que vous avez réellement déclarés, et impose une justification à chaque décision — pour que votre prochain audit ISO 27001 ou NIS2 se passe en consultant un historique, pas en fouillant des emails.</p>
            <div className="heroCtas">
              <Link href="/inscription" className="btn btn-primary btnLg">
                Créer un compte gratuitement
                <svg className="btnIco" viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
              </Link>
              <a href="#solution" className="btn btnLg">Voir comment ça marche</a>
            </div>
            <div className="trust">
              <span>Catalogue d&apos;actifs</span>
              <div className="srcs">
                <span className="src">Debian</span><span className="src">Ubuntu</span><span className="src">Windows Server</span><span className="src">PAN-OS</span><span className="src">FortiOS</span><span className="src">+ 468 autres</span>
              </div>
            </div>
          </div>

          <div className="feedMock reveal reveal-2">
            <div className="feedMockHead">
              <div className="dots"><span /><span /><span /></div>
              <span className="lbl">renseignements — en direct</span>
            </div>
            <div className="feedMockBody">
              <div className="fcard critique" style={{ animationDelay: ".1s" }}>
                <div className="fcardTop"><span className="fdot" /><span className="ftitle">CVE-2026-41823 — Windows 11</span><span className="fbadge">Nouveau</span></div>
                <div className="fmeta"><span>NVD</span><span>·</span><span className="fpill">À traiter</span></div>
              </div>
              <div className="fcard elevee" style={{ animationDelay: ".3s" }}>
                <div className="fcardTop"><span className="fdot" /><span className="ftitle">CERTFR-2026-AVI-0853 — PAN-OS</span><span className="fbadge">Nouveau</span></div>
                <div className="fmeta"><span>CERT-FR</span><span>·</span><span>CVSS 8.1</span></div>
              </div>
              <div className="fcard reglementaire" style={{ animationDelay: ".5s" }}>
                <div className="fcardTop"><span className="fdot" /><span className="ftitle">NIS2 — périmètre entités importantes</span></div>
                <div className="fmeta"><span>ANSSI</span><span>·</span><span>Réglementaire</span></div>
              </div>
              <div className="fcard moyenne" style={{ animationDelay: ".7s" }}>
                <div className="fcardTop"><span className="fdot" /><span className="ftitle">Multiples vulnérabilités — Debian LTS</span></div>
                <div className="fmeta"><span>CERT-FR</span><span>·</span><span>CVSS 5.4</span></div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <section id="probleme" className="sectionPad">
        <div className="wrap">
          <div className="sectionHead reveal">
            <div className="sectionEyebrow">Le constat</div>
            <h2>La veille cyber s&apos;éparpille, la conformité n&apos;attend pas.</h2>
            <p>Entre les CVE, les avis CERT-FR, les exigences NIS2/ISO 27001/RGPD et les bulletins éditeurs, personne ne peut tout suivre à la main — et un seul actif oublié suffit à rendre tout le reste inutile.</p>
          </div>
          <div className="problemeGrid">
            <div className="pcard reveal reveal-1">
              <div className="pcardIco"><svg viewBox="0 0 24 24"><path d="M3 3v18h18M7 16l4-6 4 3 4-7" /></svg></div>
              <h3>Six sources, zéro vue d&apos;ensemble</h3>
              <p>NVD, CERT-FR, éditeurs, ANSSI, CNIL... chacun son flux, son format, ses délais. Le croisement se fait dans la tête de quelqu&apos;un, ou pas du tout.</p>
            </div>
            <div className="pcard reveal reveal-2">
              <div className="pcardIco"><svg viewBox="0 0 24 24"><path d="M9 12l2 2 4-4M12 3l8 4v5c0 5-3.5 9-8 10-4.5-1-8-5-8-10V7l8-4z" /></svg></div>
              <h3>La conformité exige une preuve</h3>
              <p>NIS2 et ISO 27001 ne demandent pas juste d&apos;avoir traité un risque — ils demandent de prouver quand, pourquoi, et par qui.</p>
            </div>
            <div className="pcard reveal reveal-3">
              <div className="pcardIco"><svg viewBox="0 0 24 24"><path d="M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z" /></svg></div>
              <h3>Un actif oublié, un angle mort</h3>
              <p>Si personne n&apos;a déclaré ce vieux Debian 11 encore en prod, aucune alerte ne le concernera jamais — jusqu&apos;à ce que ce soit trop tard.</p>
            </div>
            <div className="pcard reveal reveal-4">
              <div className="pcardIco"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></svg></div>
              <h3>Le triage prend des heures</h3>
              <p>Chaque semaine, retrier manuellement ce qui est critique de ce qui ne l&apos;est pas — au lieu de traiter ce qui compte vraiment.</p>
            </div>
          </div>
        </div>
      </section>

      <section id="solution" className="sectionPad" style={{ background: "var(--surface)" }}>
        <div className="wrap">
          <div className="sectionHead reveal">
            <div className="sectionEyebrow">La solution</div>
            <h2>Trois étapes, entièrement automatisées.</h2>
            <p>Vous déclarez vos actifs une fois. Veille s&apos;occupe de savoir, en continu, ce qui les concerne — et garde la trace de chaque décision.</p>
          </div>
          <div className="solutionSteps">
            <div className="step reveal reveal-1">
              <div className="stepNum">01</div>
              <h3>Une base qui s&apos;enrichit toute seule</h3>
              <p>Ingestion automatique depuis NVD, CERT-FR et la CNIL, cycle après cycle — plus un catalogue de 470+ produits (OS, bases de données, pare-feux) pour ne jamais chercher en vain votre actif.</p>
              <span className="stepTag">NVD</span><span className="stepTag">CERT-FR</span><span className="stepTag">CNIL</span>
            </div>
            <div className="step reveal reveal-2">
              <div className="stepNum">02</div>
              <h3>Un matching précis, jamais approximatif</h3>
              <p>Dès qu&apos;un actif est déclaré, il est immédiatement mis en correspondance avec tout ce qui le concerne réellement — ni bruit ni angle mort, sur vos actifs et vos référentiels normatifs.</p>
              <span className="stepTag">Éditeur + produit</span><span className="stepTag">Référentiel</span>
            </div>
            <div className="step reveal reveal-3">
              <div className="stepNum">03</div>
              <h3>Un traitement qui fait preuve</h3>
              <p>Chaque changement de statut exige une justification réelle — plan d&apos;action, date, ou preuve de clôture. L&apos;historique horodaté devient votre réponse toute prête à un audit.</p>
              <span className="stepTag">Justification obligatoire</span><span className="stepTag">Export PDF</span>
            </div>
          </div>
        </div>
      </section>

      <section id="fonctionnalites" className="sectionPad">
        <div className="wrap">
          <div className="sectionHead reveal">
            <div className="sectionEyebrow">Sous le capot</div>
            <h2>Fait pour être utilisé tous les jours, pas juste pendant l&apos;audit.</h2>
          </div>
          <div className="featGrid">
            <div className="featCard span2 reveal reveal-1">
              <div className="fcBody">
                <h3>Tableau de bord</h3>
                <p>Criticités ouvertes, échéances à venir, taux de clôture — l&apos;essentiel de votre exposition en un coup d&apos;œil, jamais noyé dans le flux complet de la base.</p>
              </div>
              <div className="featMock">
                <div className="mockKpis">
                  <div className="mockKpi red"><div className="n">3</div><div className="l">Critiques</div></div>
                  <div className="mockKpi orange"><div className="n">4</div><div className="l">Élevées</div></div>
                  <div className="mockKpi blue"><div className="n">9</div><div className="l">Non consultés</div></div>
                  <div className="mockKpi violet"><div className="n">0</div><div className="l">En retard</div></div>
                </div>
              </div>
            </div>
            <div className="featCard reveal reveal-2">
              <div className="fcBody">
                <h3>Analyse CVSS visuelle</h3>
                <p>Un radar d&apos;exploitabilité et d&apos;impact calculé pour chaque vulnérabilité technique — pas juste un score brut.</p>
              </div>
              <div className="featMock">
                <div className="mockRadarRow">
                  <div className="score"><div className="n">9.8</div><div className="l">Critique</div></div>
                  <svg width="90" height="90" viewBox="0 0 220 220"><polygon points="110,46 174,110 110,174 46,110" fill="none" stroke="var(--border)" strokeWidth="1" /><polygon points="110,55 165,110 110,160 60,112" fill="rgba(255,59,59,0.25)" stroke="var(--sev-critique)" strokeWidth="1.5" /></svg>
                </div>
              </div>
            </div>
            <div className="featCard reveal reveal-3">
              <div className="fcBody">
                <h3>Catalogue d&apos;actifs auto-alimenté</h3>
                <p>Debian, Ubuntu, RHEL, PAN-OS, FortiOS et 460+ autres — recherchez, ne devinez pas la catégorie.</p>
              </div>
              <div className="featMock">
                <div className="mockSearch"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" /><path d="M21 21l-4-4" /></svg>debian</div>
                <div className="mockResult"><b>Debian</b><span>Debian Project · Système d&apos;exploitation</span></div>
              </div>
            </div>
            <div className="featCard span2 reveal reveal-4">
              <div className="fcBody">
                <h3>Traitement bloquant, pas décoratif</h3>
                <p>Impossible de clore ou démarrer un traitement sans les informations qui font foi — le statut choisi impose ce qui est demandé.</p>
              </div>
              <div className="featMock">
                <div className="mockStatuses">
                  <span className="mockPill wait">À traiter</span>
                  <span className="mockPill go">Démarré</span>
                  <span className="mockPill done">Clos</span>
                </div>
                <div className="mockJustif">« Correctif déployé le 12/09 sur le parc — CAB validé le 10/09. Preuve jointe. »</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="chiffres sectionPad">
        <div className="wrap">
          <div className="chiffresGrid">
            <div className="chiffre reveal reveal-1"><div className="n" data-count="470">0</div><div className="l">Produits catalogués automatiquement</div></div>
            <div className="chiffre reveal reveal-2"><div className="n" data-count="3">0</div><div className="l">Sources connectées en direct</div></div>
            <div className="chiffre reveal reveal-3"><div className="n" data-count="12">0</div><div className="l">Cycles de collecte par jour</div></div>
            <div className="chiffre reveal reveal-4"><div className="n" data-count="100">0</div><div className="l">% des décisions justifiées</div></div>
          </div>
        </div>
      </section>

      <section id="tarifs" className="sectionPad">
        <div className="wrap">
          <div className="sectionHead reveal">
            <div className="sectionEyebrow">Tarifs</div>
            <h2>Un prix qui suit la taille de votre parc, pas l&apos;inverse.</h2>
            <p>Trois formules, sans engagement à l&apos;aveugle — un essai gratuit sur votre premier actif déclaré.</p>
          </div>
          <div className="pricingGrid">
            <div className="priceCard reveal reveal-1">
              <h3>Essentiel</h3>
              <div className="price">149€ <small>/ mois</small></div>
              <div className="priceSub">Jusqu&apos;à 25 actifs déclarés</div>
              <ul>
                <li><Check />Ingestion NVD + CERT-FR</li>
                <li><Check />Catalogue d&apos;actifs complet</li>
                <li><Check />Workflow de traitement</li>
                <li><Check />1 utilisateur</li>
              </ul>
              <Link href="/inscription" className="btn">Commencer</Link>
            </div>
            <div className="priceCard pro reveal reveal-2">
              <span className="badgeReco">Le plus choisi</span>
              <h3>Professionnel</h3>
              <div className="price">399€ <small>/ mois</small></div>
              <div className="priceSub">Jusqu&apos;à 150 actifs, multi-clients</div>
              <ul>
                <li><Check />Tout Essentiel, plus :</li>
                <li><Check />Ingestion CNIL / RGPD</li>
                <li><Check />Export PDF d&apos;audit</li>
                <li><Check />Utilisateurs illimités</li>
                <li><Check />Support prioritaire</li>
              </ul>
              <Link href="/inscription" className="btn btn-primary">Commencer</Link>
            </div>
            <div className="priceCard reveal reveal-3">
              <h3>Entreprise</h3>
              <div className="price">Sur devis</div>
              <div className="priceSub">Parc illimité, exigences spécifiques</div>
              <ul>
                <li><Check />Tout Professionnel, plus :</li>
                <li><Check />SSO / SAML</li>
                <li><Check />SLA contractuel</li>
                <li><Check />Référentiels normatifs sur mesure</li>
              </ul>
              <a href="#contact" className="btn">Nous contacter</a>
            </div>
          </div>
        </div>
      </section>

      <section id="contact" className="sectionPad" style={{ background: "var(--surface)" }}>
        <div className="wrap">
          <div className="contactGrid">
            <div className="contactInfo reveal">
              <h2>Une question avant de vous lancer ?</h2>
              <p>Que ce soit sur un référentiel spécifique, une intégration, ou juste pour voir une démo sur votre propre parc — écrivez-nous.</p>
              <div className="contactPoint">
                <div className="contactPointIco"><svg viewBox="0 0 24 24"><path d="M4 4h16v16H4zM4 4l8 8 8-8" /></svg></div>
                <div><b>contact@veille-saas.fr</b><span>Réponse sous 24h ouvrées</span></div>
              </div>
              <div className="contactPoint">
                <div className="contactPointIco"><svg viewBox="0 0 24 24"><path d="M12 2a7 7 0 00-7 7c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 00-7-7z" /><circle cx="12" cy="9" r="2.5" /></svg></div>
                <div><b>Basés en France</b><span>Hébergement et support francophones</span></div>
              </div>
            </div>
            <div className="reveal reveal-2">
              {contactState === "ok" && <div className="formMsg success">Message envoyé — nous revenons vers vous rapidement.</div>}
              {contactState === "erreur" && <div className="formMsg error">Un problème est survenu — réessayez dans un instant.</div>}
              <form className="contactForm" onSubmit={soumettreContact}>
                <div className="fRow">
                  <div className="fGroup"><label>Nom</label><input type="text" name="nom" required /></div>
                  <div className="fGroup"><label>Email</label><input type="email" name="email" required /></div>
                </div>
                <div className="fGroup" style={{ marginBottom: 14 }}><label>Entreprise (optionnel)</label><input type="text" name="entreprise" /></div>
                <div className="fGroup" style={{ marginBottom: 18 }}><label>Message</label><textarea name="message" rows={4} required /></div>
                <button type="submit" className="btn btn-primary" style={{ width: "100%" }} disabled={contactState === "envoi"}>
                  {contactState === "envoi" ? "Envoi…" : "Envoyer le message"}
                </button>
              </form>
            </div>
          </div>
        </div>
      </section>

      <section className="ctaFinal">
        <div className="wrap reveal">
          <h2>Reprenez le contrôle de votre veille, dès aujourd&apos;hui.</h2>
          <p>Aucune carte bancaire requise pour commencer.</p>
          <Link href="/inscription" className="btn btn-primary btnLg">Créer mon compte</Link>
        </div>
      </section>

      <footer>
        <div className="wrap footerRow">
          <Link href="/" className="brand"><span className="sq">V</span>veille</Link>
          <div className="footerLinks">
            <a href="#probleme">Problématique</a>
            <a href="#solution">Solution</a>
            <a href="#tarifs">Tarifs</a>
            <a href="#contact">Contact</a>
            <Link href="/login">Connexion</Link>
          </div>
          <div className="footerCopy">© 2026 Veille — Renseignement cyber &amp; normatif.</div>
        </div>
      </footer>
    </div>
  );
}
