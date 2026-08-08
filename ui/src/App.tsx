import { useEffect, useState } from "react";

type ComponentState = "ready" | "planned" | "not_configured" | "error";

type HealthPayload = {
  status: "ok" | "degraded";
  components: Record<string, { status: ComponentState; detail: string }>;
};

const workflows = [
  {
    label: "International remote work",
    description: "Evaluate a six-week Germany request using profile, policy, security, and approval evidence.",
  },
  {
    label: "PTO request guidance",
    description: "Check balance and notice rules, then prepare a clearly labelled manager-request draft.",
  },
  {
    label: "Expense compliance",
    description: "Assess a home-office purchase against role, allowance, approval, and receipt requirements.",
  },
];

function displayName(value: string) {
  return value.replaceAll("_", " ");
}
export default function App() {
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [healthError, setHealthError] = useState(false);

  useEffect(() => {
    fetch("/health")
      .then((response) => {
        if (!response.ok) throw new Error("Health endpoint unavailable");
        return response.json() as Promise<HealthPayload>;
      })
      .then(setHealth)
      .catch(() => setHealthError(true));
  }, []);

  return (
    <main>
      <nav className="topbar" aria-label="Product navigation">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true">P</span>
          <span>PeopleOps Assistant</span>
        </div>
        <span className="milestone-pill">Foundation · v0.1.0</span>
      </nav>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Northstar Technologies · Synthetic demonstration</p>
          <h1>HR guidance grounded in policy evidence.</h1>
          <p className="hero-description">
            A transparent agentic system for policy questions and multi-step People Operations workflows.
            Every future answer will show its supporting sources and operational tool trace.
          </p>
          <div className="hero-actions" aria-label="Foundation links">
            <a className="primary-action" href="/docs">Explore API</a>
            <a className="secondary-action" href="/health">View system health</a>
          </div>
        </div>
        <aside className="evidence-card" aria-label="Foundation principles">
          <p className="card-kicker">Built for evidence</p>
          <ol>
            <li><strong>12</strong><span>synthetic policies</span></li>
            <li><strong>2</strong><span>source formats</span></li>
            <li><strong>8</strong><span>MCP tool contracts</span></li>
          </ol>
          <p className="card-note">No real employee data. No irreversible actions.</p>
        </aside>
      </section>

      <section className="section-block" aria-labelledby="readiness-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">System readiness</p>
            <h2 id="readiness-title">Honest status, component by component</h2>
          </div>
          <span className={`health-chip ${health?.status ?? "checking"}`}>
            {healthError ? "Backend offline" : health?.status === "ok" ? "Foundation healthy" : "Checking"}
          </span>
        </div>

        <div className="status-grid">
          {health ? (
            Object.entries(health.components).map(([name, component]) => (
              <article className="status-card" key={name}>
                <div className="status-label">
                  <span className={`status-dot ${component.status}`} aria-hidden="true" />
                  <h3>{displayName(name)}</h3>
                </div>
                <p>{component.detail}</p>
                <span className="status-value">{displayName(component.status)}</span>
              </article>
            ))
          ) : (
            <article className="status-card status-loading">
              <h3>{healthError ? "Health data unavailable" : "Loading readiness"}</h3>
              <p>{healthError ? "Start the FastAPI service to see live status." : "Connecting to the foundation API."}</p>
            </article>
          )}
        </div>
      </section>

      <section className="section-block workflow-section" aria-labelledby="workflow-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Planned demonstrations</p>
            <h2 id="workflow-title">Three reproducible HR workflows</h2>
          </div>
          <span className="planned-label">Implementation next</span>
        </div>
        <div className="workflow-grid">
          {workflows.map((workflow, index) => (
            <article className="workflow-card" key={workflow.label}>
              <span className="workflow-number">0{index + 1}</span>
              <h3>{workflow.label}</h3>
              <p>{workflow.description}</p>
              <span className="workflow-state">Policy + data + MCP trace</span>
            </article>
          ))}
        </div>
      </section>

      <footer>
        <span>PeopleOps Assistant</span>
        <span>Educational system · Not legal advice</span>
      </footer>
    </main>
  );
}
