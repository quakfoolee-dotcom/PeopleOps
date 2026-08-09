import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";

type ComponentState = "ready" | "planned" | "not_configured" | "error";

type HealthPayload = {
  status: "ok" | "degraded";
  app_name: string;
  version: string;
  environment: string;
  release_sha: string;
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

type PendingAction = {
  action_type: "create_mock_hr_ticket";
  confirmation_id: string;
  expires_at: string;
  summary: string;
  sanitized_arguments: Record<string, unknown>;
  confirmation_required: true;
};

type DecisionSummary = {
  status_label: string;
  duration_label: string | null;
  category_label: string | null;
  required_approvals: string[];
  clarification_needed: string[];
  next_steps: string[];
};

type GenerationMetadata = {
  mode: "deterministic" | "provider" | "deterministic_fallback";
  provider: string;
  model: string;
  resolved_model: string | null;
  duration_ms: number;
  detail: string;
};

type ChatPayload = {
  request_id: string;
  trace_id: string;
  as_of_date: string;
  status: string;
  outcome: string;
  answer: string;
  workflow: string;
  workflow_state: string;
  citations: Citation[];
  tool_trace: TraceEntry[];
  decision_summary: DecisionSummary | null;
  generation: GenerationMetadata;
  pending_action: PendingAction | null;
};

type Employee = {
  id: string;
  name: string;
  role: string;
  department: string;
  manager: string;
  location: string;
  employment: string;
  ptoDays: number;
};

type DemoTask = {
  id: string;
  number: string;
  title: string;
  employeeId: string;
  facts: string[];
  message: string;
};

const employees: Employee[] = [
  {
    id: "E-1007",
    name: "Alex Morgan",
    role: "Senior Data Analyst",
    department: "Analytics",
    manager: "Quinn Foster",
    location: "Vancouver, BC, Canada",
    employment: "Regular full-time · Remote",
    ptoDays: 13,
  },
  {
    id: "E-1021",
    name: "Logan Murphy",
    role: "Customer Success Specialist",
    department: "Customer Success",
    manager: "Kendall Price",
    location: "Toronto, ON, Canada",
    employment: "Regular full-time · Hybrid",
    ptoDays: 12,
  },
  {
    id: "E-1014",
    name: "Parker Adams",
    role: "Product Designer",
    department: "Product",
    manager: "Taylor Brooks",
    location: "Vancouver, BC, Canada",
    employment: "Regular full-time · Remote",
    ptoDays: 14,
  },
  {
    id: "E-1011",
    name: "Drew Campbell",
    role: "Quality Engineer",
    department: "Engineering",
    manager: "Rowan Kim",
    location: "Toronto, ON, Canada",
    employment: "Regular full-time · Hybrid",
    ptoDays: 10,
  },
];

const demoTasks: DemoTask[] = [
  {
    id: "remote-work",
    number: "01",
    title: "International remote work",
    employeeId: "E-1007",
    facts: ["Germany", "Six weeks"],
    message: "Can I work remotely from Germany for six weeks?",
  },
  {
    id: "pto-guidance",
    number: "02",
    title: "PTO request guidance",
    employeeId: "E-1021",
    facts: ["Sep 21–23, 2026", "Draft manager note"],
    message:
      "Can I take PTO from September 21 through September 23, 2026? Check my balance and draft a message to my manager.",
  },
  {
    id: "expense-compliance",
    number: "03",
    title: "Expense compliance",
    employeeId: "E-1014",
    facts: ["CAD 900", "Home-office chair"],
    message: "Can employee E-1014 be reimbursed for a CAD 900 home-office chair?",
  },
  {
    id: "mock-ticket",
    number: "04",
    title: "Confirmation-gated ticket",
    employeeId: "E-1011",
    facts: ["Synthetic case", "Explicit confirmation"],
    message: "Employee E-1011 reported repeated harassment. Prepare an HR ticket for the concern.",
  },
];

const initialTask = demoTasks[0];

function displayName(value: string) {
  return value.replaceAll("_", " ");
}

function workflowTitle(workflow: string) {
  const titles: Record<string, string> = {
    remote_work: "Remote-work eligibility",
    pto: "PTO guidance",
    expense: "Expense compliance",
    mock_ticket: "Mock HR ticket",
  };
  return titles[workflow] ?? "PeopleOps guidance";
}

function outcomeLabel(outcome: string) {
  const labels: Record<string, string> = {
    answered: "Guidance ready",
    conditional: "Conditionally eligible",
    draft_only: "Draft prepared · not sent",
    clarification_required: "Clarification needed",
    escalation_required: "PeopleOps review required",
    confirmation_required: "Confirmation required",
    refused: "Request not supported",
  };
  return labels[outcome] ?? displayName(outcome);
}

function workflowStatusLabel(status: string) {
  const labels: Record<string, string> = {
    completed: "Guidance complete",
    needs_clarification: "Needs details",
    escalated: "Escalated",
    out_of_scope: "Out of scope",
    awaiting_confirmation: "Awaiting confirmation",
    error: "Service unavailable",
  };
  return labels[status] ?? displayName(status);
}

function requestDetailLabel(workflow: string) {
  if (workflow === "expense") return "Amount";
  if (workflow === "mock_ticket") return "Record";
  return "Duration";
}

function readableCitationSnippet(value: string) {
  return value
    .replace(/\|\s*-{3,}\s*/g, " ")
    .replace(/\s*\|\s*/g, " · ")
    .replace(/\s+/g, " ")
    .trim();
}

async function responseError(response: Response) {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Request failed with status ${response.status}`;
  } catch {
    return `Request failed with status ${response.status}`;
  }
}

export default function App() {
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [healthError, setHealthError] = useState("");
  const [healthLoading, setHealthLoading] = useState(true);
  const [employeeId, setEmployeeId] = useState(initialTask.employeeId);
  const [message, setMessage] = useState(initialTask.message);
  const [lastQuestion, setLastQuestion] = useState(initialTask.message);
  const [lastEmployeeId, setLastEmployeeId] = useState(initialTask.employeeId);
  const [chat, setChat] = useState<ChatPayload | null>(null);
  const [chatError, setChatError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [confirmationOpen, setConfirmationOpen] = useState(false);
  const [copyState, setCopyState] = useState("Copy guidance");
  const confirmButtonRef = useRef<HTMLButtonElement>(null);

  const selectedEmployee = useMemo(
    () => employees.find((employee) => employee.id === employeeId) ?? employees[0],
    [employeeId],
  );
  const lastEmployee = useMemo(
    () => employees.find((employee) => employee.id === lastEmployeeId) ?? employees[0],
    [lastEmployeeId],
  );
  const totalTraceDuration = useMemo(
    () => chat?.tool_trace.reduce((total, entry) => total + entry.duration_ms, 0) ?? 0,
    [chat],
  );

  const refreshHealth = useCallback(async () => {
    setHealthLoading(true);
    setHealthError("");
    try {
      const response = await fetch("/health");
      if (!response.ok) throw new Error(await responseError(response));
      setHealth((await response.json()) as HealthPayload);
    } catch (error) {
      setHealthError(error instanceof Error ? error.message : "Service status unavailable.");
    } finally {
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshHealth();
  }, [refreshHealth]);

  useEffect(() => {
    if (confirmationOpen) confirmButtonRef.current?.focus();
  }, [confirmationOpen]);

  async function runChat(
    question: string,
    targetEmployeeId: string,
    options?: { requestId?: string; confirmationToken?: string; preserveResult?: boolean },
  ) {
    setSubmitting(true);
    setChatError("");
    if (!options?.preserveResult) setChat(null);
    setLastQuestion(question);
    setLastEmployeeId(targetEmployeeId);
    try {
      const body: Record<string, string> = {
        employee_id: targetEmployeeId,
        message: question,
      };
      if (options?.requestId) body.request_id = options.requestId;
      if (options?.confirmationToken) body.confirmation_token = options.confirmationToken;
      const response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error(await responseError(response));
      const payload = (await response.json()) as ChatPayload;
      setChat(payload);
      setConfirmationOpen(payload.status === "awaiting_confirmation");
      return payload;
    } catch (error) {
      setChatError(error instanceof Error ? error.message : "The request could not be completed.");
      return null;
    } finally {
      setSubmitting(false);
    }
  }

  async function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedMessage = message.trim();
    if (!normalizedMessage) return;
    await runChat(normalizedMessage, employeeId);
  }

  function loadTask(task: DemoTask) {
    setEmployeeId(task.employeeId);
    setMessage(task.message);
    setChat(null);
    setChatError("");
    setConfirmationOpen(false);
  }

  async function runTask(task: DemoTask) {
    setEmployeeId(task.employeeId);
    setMessage(task.message);
    await runChat(task.message, task.employeeId);
  }

  function startNewChat() {
    setChat(null);
    setChatError("");
    setMessage("");
    setLastQuestion("");
    setLastEmployeeId(employeeId);
    setConfirmationOpen(false);
    setCopyState("Copy guidance");
  }

  async function copyGuidance() {
    if (!chat) return;
    const copyText = `${chat.answer}\n\nRequest ID: ${chat.request_id}\nTrace ID: ${chat.trace_id}`;
    try {
      await navigator.clipboard.writeText(copyText);
      setCopyState("Copied");
    } catch {
      setCopyState("Copy unavailable");
    }
  }

  async function rerunCurrentWorkflow() {
    if (!chat || !lastQuestion) return;
    await runChat(lastQuestion, lastEmployeeId);
  }

  async function draftPeopleOpsEmail() {
    if (!chat || chat.workflow !== "remote_work" || !lastQuestion) return;
    await runChat(
      `${lastQuestion} Draft a PeopleOps follow-up email for this request.`,
      lastEmployeeId,
    );
  }

  async function confirmPendingAction() {
    if (!chat?.pending_action) return;
    setConfirming(true);
    setChatError("");
    try {
      const confirmationResponse = await fetch("/actions/mock-tickets/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          confirmation_id: chat.pending_action.confirmation_id,
          user_confirmed: true,
        }),
      });
      if (!confirmationResponse.ok) throw new Error(await responseError(confirmationResponse));
      const confirmation = (await confirmationResponse.json()) as { confirmation_token: string };
      setConfirmationOpen(false);
      await runChat(lastQuestion, lastEmployeeId, {
        requestId: chat.request_id,
        confirmationToken: confirmation.confirmation_token,
        preserveResult: true,
      });
    } catch (error) {
      setChatError(error instanceof Error ? error.message : "Confirmation could not be completed.");
    } finally {
      setConfirming(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="company-lockup">
          <span className="company-mark" aria-hidden="true">N</span>
          <span><strong>Northstar</strong><small>Technologies Inc.</small></span>
        </div>
        <div className="product-title">
          <strong>PeopleOps Assistant</strong>
          <span className="demo-badge">Demo</span>
        </div>
        <div className="synthetic-banner" role="note">
          <span aria-hidden="true">i</span>
          <span><strong>Synthetic demo environment</strong><small>No real employee data</small></span>
        </div>
        <label className="employee-menu">
          <span className="avatar" aria-hidden="true">{selectedEmployee.name.charAt(0)}</span>
          <span className="employee-menu-copy">
            <strong>{selectedEmployee.name}</strong>
            <small>{selectedEmployee.role}</small>
          </span>
          <span className="sr-only">Selected synthetic employee</span>
          <select value={employeeId} onChange={(event) => setEmployeeId(event.target.value)}>
            {employees.map((employee) => (
              <option value={employee.id} key={employee.id}>{employee.name} ({employee.id})</option>
            ))}
          </select>
        </label>
      </header>

      <div className="workspace">
        <aside className="left-rail" aria-label="Workspace navigation and demo tasks">
          <nav className="workspace-nav" aria-label="Workspace navigation">
            <a className="active" href="#chat-workspace"><span aria-hidden="true">◇</span>Chat</a>
            <a href="#demo-tasks"><span aria-hidden="true">□</span>Demo tasks</a>
            <a href="#employee-context"><span aria-hidden="true">○</span>Employee context</a>
            <a href="#system-health"><span aria-hidden="true">●</span>System health</a>
          </nav>

          <section id="demo-tasks" className="rail-section" aria-labelledby="demo-tasks-title">
            <div className="rail-heading">
              <h2 id="demo-tasks-title">Demo tasks</h2>
              <span>{demoTasks.length}</span>
            </div>
            <div className="task-list">
              {demoTasks.map((task) => (
                <article className="task-card" key={task.id}>
                  <div className="task-title"><span>{task.number}</span><strong>{task.title}</strong></div>
                  <dl>
                    <div><dt>Employee</dt><dd>{task.employeeId}</dd></div>
                    {task.facts.map((fact, index) => (
                      <div key={fact}><dt>{index === 0 ? "Detail" : "Scope"}</dt><dd>{fact}</dd></div>
                    ))}
                  </dl>
                  <div className="task-actions">
                    <button type="button" onClick={() => loadTask(task)}>Load</button>
                    <button type="button" className="run-task" onClick={() => void runTask(task)} disabled={submitting}>
                      Run task
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section id="system-health" className="rail-section health-section" aria-labelledby="health-title">
            <div className="rail-heading">
              <h2 id="health-title">System health</h2>
              <button type="button" onClick={() => void refreshHealth()} disabled={healthLoading}>
                {healthLoading ? "Checking" : "Refresh"}
              </button>
            </div>
            {healthError ? (
              <p className="health-error" role="alert">{healthError}</p>
            ) : (
              <ul className="health-list">
                {Object.entries(health?.components ?? {}).map(([name, component]) => (
                  <li key={name}>
                    <span className={`health-dot ${component.status}`} aria-hidden="true" />
                    <span>{displayName(name)}</span>
                    <strong>{displayName(component.status)}</strong>
                  </li>
                ))}
              </ul>
            )}
            {health && (
              <p className="health-meta">v{health.version} · {health.environment} · {health.status}<br />release {health.release_sha.slice(0, 7)}</p>
            )}
          </section>
        </aside>

        <main id="chat-workspace" className="conversation-column">
          <div className="conversation-header">
            <div>
              <p className="section-kicker">Evidence-first workspace</p>
              <h1>Chat with PeopleOps Assistant</h1>
              <p>Grounded HR policy guidance through bounded MCP workflows.</p>
            </div>
            <button className="secondary-button" type="button" onClick={startNewChat}>＋ New chat</button>
          </div>

          <section className="chat-stream" aria-live="polite" aria-busy={submitting || confirming}>
            {!chat && !chatError && !submitting && (
              <div className="welcome-message">
                <span className="assistant-orb" aria-hidden="true">✦</span>
                <div>
                  <h2>Ready for a grounded HR question</h2>
                  <p>Choose a demo task or enter a question. Every result shows its exact sources, MCP operations, and safety state.</p>
                </div>
              </div>
            )}

            {(chat || submitting) && lastQuestion && (
              <article className="message-card user-message">
                <span className="avatar small" aria-hidden="true">{lastEmployee.name.charAt(0)}</span>
                <div><div className="message-author"><strong>You</strong><span>{lastEmployee.id}</span></div><p>{lastQuestion}</p></div>
              </article>
            )}

            {submitting && !confirming && (
              <article className="message-card assistant-message loading-message">
                <span className="assistant-orb small" aria-hidden="true">✦</span>
                <div><strong>PeopleOps Assistant</strong><p>Discovering tools and checking policy evidence…</p></div>
              </article>
            )}

            {chatError && (
              <div className="inline-error" role="alert">
                <strong>Request unavailable</strong><p>{chatError}</p>
              </div>
            )}

            {chat && !submitting && (
              <article className="message-card assistant-message">
                <span className="assistant-orb small" aria-hidden="true">✦</span>
                <div className="assistant-content">
                  <div className="message-author">
                    <strong>PeopleOps Assistant</strong>
                    <span className={`generation-badge ${chat.generation.mode}`} title={chat.generation.detail}>
                      {chat.generation.mode === "provider"
                        ? `${displayName(chat.generation.provider)} · ${chat.generation.resolved_model ?? chat.generation.model}`
                        : chat.generation.mode === "deterministic_fallback"
                          ? "Verified fallback"
                          : "Verified deterministic"}
                    </span>
                    <span>As of {chat.as_of_date}</span>
                  </div>
                  <section className={`result-card outcome-${chat.outcome}`} aria-labelledby="result-title">
                    <div className="result-card-header">
                      <span className="result-icon" aria-hidden="true">✓</span>
                      <div><p>{workflowTitle(chat.workflow)}</p><h2 id="result-title">{outcomeLabel(chat.outcome)}</h2></div>
                      <span className="state-pill">{workflowStatusLabel(chat.status)}</span>
                    </div>
                    {chat.decision_summary && (
                      <div className="decision-summary">
                        <dl className="decision-facts">
                          <div><dt>Status</dt><dd>{chat.decision_summary.status_label}</dd></div>
                          <div><dt>{requestDetailLabel(chat.workflow)}</dt><dd>{chat.decision_summary.duration_label ?? "Not applicable"}</dd></div>
                          <div><dt>Category</dt><dd>{chat.decision_summary.category_label ?? "General guidance"}</dd></div>
                        </dl>

                        {chat.decision_summary.required_approvals.length > 0 && (
                          <section className="decision-row" aria-labelledby="approvals-title">
                            <h3 id="approvals-title">Required approvals</h3>
                            <div className="approval-list">
                              {chat.decision_summary.required_approvals.map((approval) => <span key={approval}>✓ {approval}</span>)}
                            </div>
                          </section>
                        )}

                        {chat.decision_summary.clarification_needed.length > 0 && (
                          <section className="clarification-row" aria-labelledby="clarification-title">
                            <span aria-hidden="true">!</span>
                            <div><h3 id="clarification-title">Clarification needed</h3><p>{chat.decision_summary.clarification_needed.join(" · ")}</p></div>
                          </section>
                        )}
                      </div>
                    )}

                    <div className="guidance-copy"><h3>Guidance</h3><p className="answer-text">{chat.answer}</p></div>

                    {chat.decision_summary?.next_steps.length ? (
                      <section className="next-steps" aria-labelledby="next-steps-title">
                        <h3 id="next-steps-title">Next steps</h3>
                        <ol>{chat.decision_summary.next_steps.map((step) => <li key={step}>{step}</li>)}</ol>
                      </section>
                    ) : null}
                  </section>

                  <div className="source-strip" aria-label="Cited policy sections">
                    {chat.citations.map((citation) => (
                      <a href={`#citation-${citation.chunk_id}`} key={citation.chunk_id}>
                        <span>{citation.policy_id}</span><strong>§ {citation.section_id}</strong>
                      </a>
                    ))}
                    {chat.citations.length === 0 && <span className="no-sources">No citations returned for this controlled response.</span>}
                  </div>

                  <div className="response-actions">
                    <button type="button" onClick={() => void copyGuidance()}>{copyState}</button>
                    {chat.workflow === "remote_work" && chat.outcome === "conditional" && (
                      <button type="button" onClick={() => void draftPeopleOpsEmail()}>Draft PeopleOps email</button>
                    )}
                    {["remote_work", "pto", "expense"].includes(chat.workflow) && (
                      <button type="button" onClick={() => void rerunCurrentWorkflow()}>Re-run {workflowTitle(chat.workflow).toLowerCase()}</button>
                    )}
                    {chat.pending_action && (
                      <button className="primary-button" type="button" onClick={() => setConfirmationOpen(true)}>
                        Review pending action
                      </button>
                    )}
                    <button type="button" onClick={startNewChat}>Ask another question</button>
                  </div>

                  <div className="result-metrics" aria-label="Operational evidence summary">
                    <span><strong>{chat.citations.length}</strong> cited sections</span>
                    <span><strong>{chat.tool_trace.length}</strong> MCP operations</span>
                    <span>
                      <strong>{chat.generation.mode === "provider" ? `${chat.generation.duration_ms} ms` : `${totalTraceDuration} ms`}</strong>
                      {chat.generation.mode === "provider" ? "provider synthesis" : "traced tool time"}
                    </span>
                  </div>

                  <dl className="identifier-row">
                    <div><dt>Request ID</dt><dd>{chat.request_id}</dd></div>
                    <div><dt>Trace ID</dt><dd>{chat.trace_id}</dd></div>
                  </dl>
                </div>
              </article>
            )}
          </section>

          <form className="composer" onSubmit={submitQuestion}>
            <label htmlFor="question">Ask a follow-up or start another workflow</label>
            <div className="composer-row">
              <textarea
                id="question"
                rows={3}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Ask about remote work, PTO, expenses, or prepare a mock HR ticket…"
              />
              <button className="send-button" disabled={submitting || confirming || !message.trim()} type="submit">
                <span className="sr-only">Send question</span><span aria-hidden="true">➤</span>
              </button>
            </div>
            <div className="composer-meta">
              <span>Employee: <strong>{selectedEmployee.id}</strong></span>
              <span>Demo policy as-of date: <strong>2026-09-01</strong></span>
            </div>
          </form>
          <p className="assistant-disclaimer">PeopleOps Assistant can make mistakes. Review citations and verify guidance before acting.</p>

          <section id="employee-context" className="context-panel" aria-labelledby="context-title">
            <div className="context-heading"><div><p className="section-kicker">Selected employee</p><h2 id="context-title">Context</h2></div><span>{selectedEmployee.id}</span></div>
            <div className="context-grid">
              <article><span aria-hidden="true">○</span><div><small>Employee</small><strong>{selectedEmployee.name}</strong><p>{selectedEmployee.role}<br />{selectedEmployee.department}</p></div></article>
              <article><span aria-hidden="true">□</span><div><small>PTO balance</small><strong>{selectedEmployee.ptoDays} days</strong><p>Available on demo policy date</p></div></article>
              <article><span aria-hidden="true">◇</span><div><small>Manager</small><strong>{selectedEmployee.manager}</strong><p>Current reporting line</p></div></article>
              <article><span aria-hidden="true">⌖</span><div><small>Home office</small><strong>{selectedEmployee.location}</strong><p>Registered location</p></div></article>
              <article><span aria-hidden="true">▣</span><div><small>Employment</small><strong>{selectedEmployee.employment}</strong><p>Active synthetic record</p></div></article>
            </div>
          </section>
        </main>

        <aside className="evidence-rail" aria-label="Citations and operational evidence">
          <details className="inspector-panel" open>
            <summary><span>Citations <strong>({chat?.citations.length ?? 0})</strong></span><span aria-hidden="true">⌃</span></summary>
            <div className="citation-list">
              {chat?.citations.map((citation, index) => (
                <article id={`citation-${citation.chunk_id}`} className="citation-item" key={citation.chunk_id}>
                  <span className="citation-number">{index + 1}</span>
                  <div>
                    <div className="citation-meta"><strong>{citation.policy_id}</strong><span>v{citation.version}</span><span>{citation.source_format.toUpperCase()}</span></div>
                    <h2>{citation.title}</h2>
                    <p className="citation-snippet"><strong>§ {citation.section_id}</strong> {readableCitationSnippet(citation.snippet)}</p>
                    <small>Effective {citation.effective_date}{citation.page ? ` · page ${citation.page}` : ""} · score {citation.retrieval_score.toFixed(3)}</small>
                    <details className="full-snippet"><summary>Full cited snippet</summary><p>{citation.snippet}</p></details>
                    <details className="source-detail"><summary>Source metadata</summary><code>{citation.chunk_id}<br />{citation.source_path}</code></details>
                  </div>
                </article>
              ))}
              {!chat?.citations.length && <p className="empty-inspector">Cited policy sections will appear after a workflow runs.</p>}
            </div>
          </details>

          <details className="inspector-panel trace-panel" open>
            <summary><span>Tool trace <strong>({chat?.tool_trace.length ?? 0})</strong></span><span aria-hidden="true">⌃</span></summary>
            <ol className="tool-trace">
              {chat?.tool_trace.map((entry) => (
                <li key={`${entry.sequence}-${entry.tool_name}`}>
                  <span className={`trace-marker ${entry.status}`} aria-hidden="true">✓</span>
                  <div>
                    <div className="tool-name"><span>{entry.sequence}</span><strong>{displayName(entry.tool_name)}</strong><small>{entry.duration_ms} ms</small></div>
                    <p>{entry.result_summary}</p>
                    <details><summary>Sanitized arguments</summary><code>{JSON.stringify(entry.sanitized_arguments, null, 2)}</code></details>
                    {entry.error_code && <span className="error-code">{entry.error_code}</span>}
                  </div>
                </li>
              ))}
            </ol>
            {!chat?.tool_trace.length && <p className="empty-inspector">Actual MCP discovery and tool calls will appear here. Hidden reasoning is never shown.</p>}
            {chat && <div className="trace-footer"><span>Total tool time: {totalTraceDuration} ms</span><span>Trace: {chat.trace_id.slice(0, 8)}</span></div>}
          </details>
        </aside>
      </div>

      {chat?.pending_action && confirmationOpen && (
        <div className="confirmation-backdrop">
          <section
            className="confirmation-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirmation-title"
            aria-describedby="confirmation-note"
            onKeyDown={(event) => {
              if (event.key === "Escape" && !confirming) setConfirmationOpen(false);
            }}
          >
            <button className="close-dialog" type="button" aria-label="Close confirmation" onClick={() => setConfirmationOpen(false)}>×</button>
            <p className="section-kicker">Explicit confirmation required</p>
            <h2 id="confirmation-title">Create mock HR ticket?</h2>
            <div className="demo-warning"><span aria-hidden="true">i</span><p><strong>Demonstration action only.</strong> No production HR system or real employee record will be changed.</p></div>
            <p className="confirmation-summary">{chat.pending_action.summary}</p>
            <dl className="action-preview">
              {Object.entries(chat.pending_action.sanitized_arguments).map(([key, value]) => (
                <div key={key}><dt>{displayName(key)}</dt><dd>{String(value)}</dd></div>
              ))}
              <div><dt>Expires</dt><dd>{new Date(chat.pending_action.expires_at).toLocaleString()}</dd></div>
            </dl>
            <p id="confirmation-note" className="confirmation-note">The action remains blocked until you confirm. The signed confirmation token is never displayed or written to the operational trace.</p>
            <div className="confirmation-actions">
              <button type="button" onClick={() => setConfirmationOpen(false)} disabled={confirming}>Cancel</button>
              <button ref={confirmButtonRef} className="primary-button" type="button" onClick={() => void confirmPendingAction()} disabled={confirming}>
                {confirming ? "Creating mock ticket…" : "Confirm mock ticket"}
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
