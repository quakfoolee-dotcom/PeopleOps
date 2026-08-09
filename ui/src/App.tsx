import { useEffect, useState, type FormEvent } from "react";

type ComponentState = "ready" | "planned" | "not_configured" | "error";

type HealthPayload = {
  status: "ok" | "degraded";
  components: Record<string, { status: ComponentState; detail: string }>;
};

type Citation = {
  policy_id: string;
  section_id: string;
  title: string;
  snippet: string;
  version: string;
  effective_date: string;
  source_format: "markdown" | "pdf";
  source_path: string;
  page: number | null;
  chunk_id: string;
  retrieval_score: number;
};

type TraceEntry = {
  sequence: number;
  tool_name: string;
  sanitized_arguments: Record<string, unknown>;
  status: "succeeded" | "failed" | "timed_out" | "denied";
  result_summary: string;
  duration_ms: number;
  error_code: string | null;
};

type ChatPayload = {
  request_id: string;
  as_of_date: string;
  status: string;
  outcome: string;
  answer: string;
  citations: Citation[];
  tool_trace: TraceEntry[];
};

const demoMessage = "Can I work remotely from Germany for six weeks?";

const workflows = [
  {
    label: "International remote work",
    description: "Evaluate a six-week Germany request using profile and policy evidence.",
    state: "Live · hybrid RAG + 8 MCP tools",
  },
  {
    label: "PTO request guidance",
    description: "Check balance and notice rules, then prepare a clearly labelled manager-request draft.",
    state: "Planned workflow",
  },
  {
    label: "Expense compliance",
    description: "Assess a home-office purchase against role, allowance, approval, and receipt requirements.",
    state: "Planned workflow",
  },
];

function displayName(value: string) {
  return value.replaceAll("_", " ");
}

export default function App() {
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [employeeId, setEmployeeId] = useState("E-1007");
  const [message, setMessage] = useState(demoMessage);
  const [chat, setChat] = useState<ChatPayload | null>(null);
  const [chatError, setChatError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetch("/health")
      .then((response) => {
        if (!response.ok) throw new Error("Health endpoint unavailable");
        return response.json() as Promise<HealthPayload>;
      })
      .then(setHealth)
      .catch(() => setHealthError(true));
  }, []);

  async function submitDemo(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setChatError("");
    setChat(null);
    try {
      const response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ employee_id: employeeId, message }),
      });
      if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
      setChat((await response.json()) as ChatPayload);
    } catch (error) {
      setChatError(error instanceof Error ? error.message : "The request could not be completed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main>
      <nav className="topbar" aria-label="Product navigation">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true">P</span>
          <span>PeopleOps Assistant</span>
        </div>
        <span className="milestone-pill">Phase 6 · v0.3.0</span>
      </nav>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Northstar Technologies · Synthetic demonstration</p>
          <h1>HR guidance grounded in policy evidence.</h1>
          <p className="hero-description">
            A transparent People Operations assistant for policy questions and bounded workflows.
            The live demonstration shows its supporting sources and MCP operational trace.
          </p>
          <div className="hero-actions" aria-label="Product links">
            <a className="primary-action" href="#live-demo">Run live demonstration</a>
            <a className="secondary-action" href="/docs">Explore API</a>
            <a className="secondary-action" href="/health">View system health</a>
          </div>
        </div>
        <aside className="evidence-card" aria-label="Evidence summary">
          <p className="card-kicker">Built for evidence</p>
          <ol>
            <li><strong>12</strong><span>synthetic policies</span></li>
            <li><strong>25</strong><span>gold evaluation cases</span></li>
            <li><strong>2</strong><span>live MCP tools</span></li>
          </ol>
          <p className="card-note">No real employee data. No irreversible actions.</p>
        </aside>
      </section>

      <section id="live-demo" className="section-block demo-section" aria-labelledby="demo-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Thin vertical slice</p>
            <h2 id="demo-title">Trace a request from question to evidence</h2>
          </div>
          <span className="live-label">Live</span>
        </div>

        <div className="demo-layout">
          <form className="request-panel" onSubmit={submitDemo}>
            <div className="field-group">
              <label htmlFor="employee-id">Synthetic employee</label>
              <select
                id="employee-id"
                value={employeeId}
                onChange={(event) => setEmployeeId(event.target.value)}
              >
                <option value="E-1007">E-1007 · Alex Morgan · Vancouver</option>
                <option value="E-9999">E-9999 · Unknown employee test</option>
              </select>
            </div>
            <div className="field-group">
              <label htmlFor="request-message">People Operations question</label>
              <textarea
                id="request-message"
                rows={5}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
              />
            </div>
            <p className="form-note">
              The current workflow is intentionally bounded; all eight Phase 6 MCP tools are now available.
            </p>
            <button className="submit-action" disabled={submitting || !message.trim()} type="submit">
              {submitting ? "Tracing request…" : "Run cited workflow"}
            </button>
          </form>

          <div className="response-panel" aria-live="polite">
            {!chat && !chatError && (
              <div className="response-empty">
                <span className="trace-glyph" aria-hidden="true">↗</span>
                <h3>Ready to trace</h3>
                <p>The result will include the answer, exact policy sections, and all MCP operations.</p>
              </div>
            )}
            {chatError && (
              <div className="response-error" role="alert">
                <h3>Request unavailable</h3>
                <p>{chatError}</p>
              </div>
            )}
            {chat && (
              <div className="response-content">
                <div className="response-meta">
                  <span className={`outcome-chip ${chat.status}`}>{displayName(chat.outcome)}</span>
                  <span>As of {chat.as_of_date}</span>
                </div>
                <h3>PeopleOps guidance</h3>
                <p className="answer-text">{chat.answer}</p>
                <p className="request-id">Request ID: {chat.request_id}</p>
              </div>
            )}
          </div>
        </div>

        {chat && chat.citations.length > 0 && (
          <div className="evidence-results">
            <div className="result-heading">
              <p className="eyebrow">Cited evidence</p>
              <span>{chat.citations.length} sections</span>
            </div>
            <div className="citation-grid">
              {chat.citations.map((citation) => (
                <article className="citation-card" key={`${citation.policy_id}-${citation.section_id}`}>
                  <div className="citation-id">
                    <span>{citation.policy_id}</span>
                    <strong>{citation.section_id}</strong>
                  </div>
                  <h3>{citation.title}</h3>
                  <p>{citation.snippet}</p>
                  <small>
                    v{citation.version} · effective {citation.effective_date} · {citation.source_format}
                    {citation.page ? ` · page ${citation.page}` : ""} · score {citation.retrieval_score.toFixed(3)}
                    <br />{citation.chunk_id} · {citation.source_path}
                  </small>
                </article>
              ))}
            </div>
          </div>
        )}

        {chat && (
          <div className="trace-results">
            <div className="result-heading">
              <p className="eyebrow">Operational trace</p>
              <span>{chat.tool_trace.length} operations</span>
            </div>
            <ol className="trace-list">
              {chat.tool_trace.map((entry) => (
                <li key={entry.sequence}>
                  <span className="trace-number">{entry.sequence}</span>
                  <div>
                    <div className="trace-title">
                      <strong>{displayName(entry.tool_name)}</strong>
                      <span className={`trace-status ${entry.status}`}>{entry.status}</span>
                      <small>{entry.duration_ms} ms</small>
                    </div>
                    <p>{entry.result_summary}</p>
                    {Object.keys(entry.sanitized_arguments).length > 0 && (
                      <code>{JSON.stringify(entry.sanitized_arguments)}</code>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </div>
        )}
      </section>

      <section className="section-block" aria-labelledby="readiness-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">System readiness</p>
            <h2 id="readiness-title">Honest status, component by component</h2>
          </div>
          <span className={`health-chip ${health?.status ?? "checking"}`}>
            {healthError ? "Backend offline" : health?.status === "ok" ? "Service healthy" : "Checking"}
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
              <p>{healthError ? "Start the FastAPI service to see live status." : "Connecting to the service API."}</p>
            </article>
          )}
        </div>
      </section>

      <section className="section-block workflow-section" aria-labelledby="workflow-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Demonstration roadmap</p>
            <h2 id="workflow-title">Three reproducible HR workflows</h2>
          </div>
          <span className="planned-label">1 live · 2 planned</span>
        </div>
        <div className="workflow-grid">
          {workflows.map((workflow, index) => (
            <article className="workflow-card" key={workflow.label}>
              <span className="workflow-number">0{index + 1}</span>
              <h3>{workflow.label}</h3>
              <p>{workflow.description}</p>
              <span className="workflow-state">{workflow.state}</span>
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
