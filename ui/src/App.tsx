import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";

type ComponentState = "ready" | "planned" | "not_configured" | "error";

type HealthPayload = {
  status: "ok" | "degraded";
  app_name: string;
  version: string;
  environment: string;
  release_sha: string;
  components: Record<string, { status: ComponentState; detail: string }>;
};

const primaryHealthComponents = [
  { key: "mcp", label: "MCP Connectivity" },
  { key: "rag_index", label: "RAG Index" },
  { key: "mock_database", label: "Mock Database" },
  { key: "llm_provider", label: "LLM Provider" },
] as const;

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

type UseCase = "auto" | "remote_work" | "pto" | "expense" | "benefits_policy" | "workplace_concern";

type AttachmentContext = {
  filename: string;
  media_type: "text/plain" | "text/markdown" | "application/pdf";
  extracted_text: string;
  original_size_bytes: number;
  truncated: boolean;
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
  benefits: string;
};

type DemoTask = {
  id: string;
  number: string;
  title: string;
  employeeId: string | null;
  facts: string[];
  message: string;
  useCase: UseCase;
};

const useCaseOptions: Array<{ value: UseCase; label: string; starter: string }> = [
  { value: "auto", label: "Auto-detect", starter: "" },
  { value: "remote_work", label: "International remote work", starter: "Can I work remotely from another country?" },
  { value: "pto", label: "PTO guidance", starter: "Can you check my PTO request and balance?" },
  { value: "expense", label: "Expense reimbursement", starter: "Is this expense eligible for reimbursement?" },
  { value: "benefits_policy", label: "Benefits and policy", starter: "What benefits or policy guidance applies?" },
  { value: "workplace_concern", label: "Workplace concern", starter: "Help me prepare a confidential workplace concern." },
];

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
    benefits: "Enrolled · Employee coverage",
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
    benefits: "Enrolled · Employee coverage",
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
    benefits: "Enrolled · Employee coverage",
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
    benefits: "Enrolled · Employee + one",
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
    useCase: "remote_work",
  },
  {
    id: "pto-guidance",
    number: "02",
    title: "PTO request guidance",
    employeeId: "E-1021",
    facts: ["Sep 21–23, 2026", "Draft manager note"],
    message:
      "Can I take PTO from September 21 through September 23, 2026? Check my balance and draft a message to my manager.",
    useCase: "pto",
  },
  {
    id: "expense-compliance",
    number: "03",
    title: "Expense compliance",
    employeeId: "E-1014",
    facts: ["CAD 900", "Home-office chair"],
    message: "Can employee E-1014 be reimbursed for a CAD 900 home-office chair?",
    useCase: "expense",
  },
  {
    id: "mock-ticket",
    number: "04",
    title: "Confirmation-gated ticket",
    employeeId: "E-1011",
    facts: ["Synthetic case", "Explicit confirmation"],
    message: "Employee E-1011 reported repeated harassment. Prepare an HR ticket for the concern.",
    useCase: "workplace_concern",
  },
  {
    id: "policy-benefits",
    number: "05",
    title: "Policy and benefits guidance",
    employeeId: null,
    facts: ["BEN-5", "31-day enrollment window"],
    message: "How long does a newly eligible employee have to complete benefits enrollment?",
    useCase: "benefits_policy",
  },
];

const initialTask = demoTasks[0];

function displayName(value: string) {
  return value.replaceAll("_", " ");
}

function healthStatusLabel(status: ComponentState) {
  const labels: Record<ComponentState, string> = {
    ready: "Healthy",
    planned: "Planned",
    not_configured: "Not configured",
    error: "Unavailable",
  };
  return labels[status];
}

function healthCheckedLabel(value: Date) {
  return value.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function workflowTitle(workflow: string) {
  const titles: Record<string, string> = {
    policy: "Policy guidance",
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

type GuidanceContent = {
  summary: string[];
  verified: string[];
  hasGeneratedSummary: boolean;
};

const generatedSummaryHeading = "AI-generated grounded summary";
const verifiedResultHeading = "Verified workflow result";

function sentenceItems(value: string) {
  const normalized = value
    .replace(/\bnot approval\./i, "This result is guidance, not approval.")
    .replace(/([a-z])_([a-z])/g, "$1 $2")
    .replace(/\s+/g, " ")
    .trim();
  if (!normalized) return [];

  return (
    normalized.match(/.+?(?:[.!?](?=\s+[A-Z0-9])|$)/g)?.map((item) => item.trim()).filter(Boolean)
    ?? [normalized]
  );
}

function guidanceContent(answer: string): GuidanceContent {
  const generatedStart = answer.indexOf(generatedSummaryHeading);
  const verifiedStart = answer.indexOf(verifiedResultHeading);

  if (generatedStart !== -1 && verifiedStart > generatedStart) {
    const summaryText = answer.slice(generatedStart + generatedSummaryHeading.length, verifiedStart);
    const verifiedText = answer.slice(verifiedStart + verifiedResultHeading.length);
    return {
      summary: sentenceItems(summaryText),
      verified: sentenceItems(verifiedText),
      hasGeneratedSummary: true,
    };
  }

  return {
    summary: sentenceItems(answer),
    verified: [],
    hasGeneratedSummary: false,
  };
}

function normalizedFact(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/[^a-z0-9/]+/gi, " ")
    .trim()
    .toLocaleLowerCase();
}

function distinctSummaryItems(items: string[], decisionSummary: DecisionSummary | null) {
  if (!decisionSummary) return items;

  const displayedFacts = new Set(
    [
      decisionSummary.status_label,
      decisionSummary.duration_label,
      decisionSummary.category_label,
      ...decisionSummary.required_approvals,
    ]
      .filter((value): value is string => Boolean(value))
      .map(normalizedFact),
  );

  const distinctItems = items.filter((item) => {
    const normalized = normalizedFact(item);
    return !displayedFacts.has(normalized) && !normalized.startsWith("verified sources");
  });

  return distinctItems.length > 0 ? distinctItems : items.slice(0, 1);
}

function GuidanceSection({ answer, decisionSummary }: { answer: string; decisionSummary: DecisionSummary | null }) {
  const content = guidanceContent(answer);
  const visibleSummary = distinctSummaryItems(content.summary, decisionSummary);
  const [lead, ...supportingPoints] = visibleSummary;

  return (
    <div className="guidance-copy" aria-labelledby="guidance-title">
      <div className="guidance-heading">
        <div>
          <h3 id="guidance-title">{content.hasGeneratedSummary ? "Plain-language summary" : "Guidance"}</h3>
          <p>{content.hasGeneratedSummary ? "Grounded in the verified workflow and cited policies" : "What this result means"}</p>
        </div>
        {content.hasGeneratedSummary && <span>AI summarized</span>}
      </div>

      {lead && <p className="guidance-lead">{lead}</p>}
      {supportingPoints.length > 0 && (
        <ul className="guidance-points">
          {supportingPoints.map((point, index) => <li key={`${index}-${point}`}>{point}</li>)}
        </ul>
      )}

      {content.verified.length > 0 && (
        <details className="verified-guidance">
          <summary>
            <span className="verified-icon" aria-hidden="true">✓</span>
            <span><strong>Why this result</strong><small>Verified workflow rationale</small></span>
            <span className="details-chevron" aria-hidden="true">⌄</span>
          </summary>
          <ul>
            {content.verified.map((point, index) => <li key={`${index}-${point}`}>{point}</li>)}
          </ul>
        </details>
      )}
    </div>
  );
}

type NavIconName = "chat" | "tasks" | "requests" | "profile" | "calendar" | "benefits" | "help" | "settings";

function NavIcon({ name }: { name: NavIconName }) {
  const common = { fill: "none", stroke: "currentColor", strokeLinecap: "round" as const, strokeLinejoin: "round" as const, strokeWidth: 1.8 };
  const paths: Record<NavIconName, ReactNode> = {
    chat: <><path {...common} d="M4 5.5A2.5 2.5 0 0 1 6.5 3h7A2.5 2.5 0 0 1 16 5.5v4A2.5 2.5 0 0 1 13.5 12H9l-4 3v-3.7A2.5 2.5 0 0 1 4 9.5z" /></>,
    tasks: <><rect {...common} x="4" y="4" width="12" height="13" rx="2" /><path {...common} d="m7 9 1.5 1.5L12 7" /></>,
    requests: <><path {...common} d="M6 3h6l3 3v11H6z" /><path {...common} d="M12 3v4h4M8.5 11h4M8.5 14h3" /></>,
    profile: <><circle {...common} cx="10" cy="6.5" r="3" /><path {...common} d="M4.5 17a5.5 5.5 0 0 1 11 0" /></>,
    calendar: <><rect {...common} x="3.5" y="5" width="13" height="12" rx="2" /><path {...common} d="M6.5 3v4M13.5 3v4M3.5 9h13" /></>,
    benefits: <><path {...common} d="M10 17S3.5 13.3 3.5 8a3.5 3.5 0 0 1 6.5-1.8A3.5 3.5 0 0 1 16.5 8C16.5 13.3 10 17 10 17z" /></>,
    help: <><circle {...common} cx="10" cy="10" r="7" /><path {...common} d="M8.2 8a2 2 0 1 1 2.4 2c-.6.2-.9.6-.9 1.3M10 14h.01" /></>,
    settings: <><circle {...common} cx="10" cy="10" r="2.5" /><path {...common} d="M10 2.8v2M10 15.2v2M17.2 10h-2M4.8 10h-2M15.1 4.9l-1.4 1.4M6.3 13.7l-1.4 1.4M15.1 15.1l-1.4-1.4M6.3 6.3 4.9 4.9" /></>,
  };
  return <svg className="nav-icon" viewBox="0 0 20 20" aria-hidden="true">{paths[name]}</svg>;
}

function ActionButton({ icon, title, subtitle, onClick, primary = false }: { icon: string; title: string; subtitle: string; onClick: () => void; primary?: boolean }) {
  return (
    <button aria-label={title} className={primary ? "primary-button" : undefined} type="button" onClick={onClick}>
      <span className="action-icon" aria-hidden="true">{icon}</span>
      <span><strong>{title}</strong><small>{subtitle}</small></span>
    </button>
  );
}

function attachmentMediaType(file: File): AttachmentContext["media_type"] | null {
  const suffix = file.name.split(".").pop()?.toLocaleLowerCase();
  if (suffix === "txt") return "text/plain";
  if (suffix === "md") return "text/markdown";
  if (suffix === "pdf") return "application/pdf";
  return null;
}

async function fileToBase64(file: File) {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  const chunkSize = 32_768;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(index, index + chunkSize));
  }
  return btoa(binary);
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
  const [healthCheckedAt, setHealthCheckedAt] = useState<Date | null>(null);
  const [employeeId, setEmployeeId] = useState(initialTask.employeeId ?? employees[0].id);
  const [message, setMessage] = useState(initialTask.message);
  const [useCase, setUseCase] = useState<UseCase>(initialTask.useCase);
  const [attachment, setAttachment] = useState<AttachmentContext | null>(null);
  const [attachmentError, setAttachmentError] = useState("");
  const [attachmentLoading, setAttachmentLoading] = useState(false);
  const [lastQuestion, setLastQuestion] = useState(initialTask.message);
  const [lastEmployeeId, setLastEmployeeId] = useState<string | null>(initialTask.employeeId);
  const [lastUseCase, setLastUseCase] = useState<UseCase>(initialTask.useCase);
  const [lastAttachment, setLastAttachment] = useState<AttachmentContext | null>(null);
  const [chat, setChat] = useState<ChatPayload | null>(null);
  const [chatError, setChatError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [confirmationOpen, setConfirmationOpen] = useState(false);
  const [copyState, setCopyState] = useState("Save conversation");
  const [demoTasksOpen, setDemoTasksOpen] = useState(true);
  const confirmButtonRef = useRef<HTMLButtonElement>(null);
  const employeeSelectRef = useRef<HTMLSelectElement>(null);
  const attachmentInputRef = useRef<HTMLInputElement>(null);

  const selectedEmployee = useMemo(
    () => employees.find((employee) => employee.id === employeeId) ?? employees[0],
    [employeeId],
  );
  const lastEmployee = useMemo(
    () => employees.find((employee) => employee.id === lastEmployeeId) ?? null,
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
      setHealthCheckedAt(new Date());
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
    targetEmployeeId: string | null,
    options?: {
      requestId?: string;
      confirmationToken?: string;
      preserveResult?: boolean;
      useCase?: UseCase;
      attachment?: AttachmentContext | null;
    },
  ) {
    const requestUseCase = options?.useCase ?? useCase;
    const requestAttachment = options?.attachment === undefined ? attachment : options.attachment;
    setSubmitting(true);
    setChatError("");
    if (!options?.preserveResult) setChat(null);
    setLastQuestion(question);
    setLastEmployeeId(targetEmployeeId);
    setLastUseCase(requestUseCase);
    setLastAttachment(requestAttachment);
    try {
      const body: Record<string, unknown> = { message: question, use_case: requestUseCase };
      if (targetEmployeeId) body.employee_id = targetEmployeeId;
      if (requestAttachment) body.attachment = requestAttachment;
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
    await runChat(normalizedMessage, employeeId, { useCase, attachment });
  }

  function loadTask(task: DemoTask) {
    if (task.employeeId) setEmployeeId(task.employeeId);
    setMessage(task.message);
    setUseCase(task.useCase);
    setAttachment(null);
    setAttachmentError("");
    setChat(null);
    setChatError("");
    setConfirmationOpen(false);
  }

  async function runTask(task: DemoTask) {
    if (task.employeeId) setEmployeeId(task.employeeId);
    setMessage(task.message);
    setUseCase(task.useCase);
    setAttachment(null);
    setAttachmentError("");
    await runChat(task.message, task.employeeId, { useCase: task.useCase, attachment: null });
  }

  function startNewChat() {
    setChat(null);
    setChatError("");
    setMessage("");
    setUseCase("auto");
    setAttachment(null);
    setAttachmentError("");
    setLastQuestion("");
    setLastEmployeeId(employeeId);
    setConfirmationOpen(false);
    setCopyState("Save conversation");
  }

  async function copyGuidance() {
    if (!chat) return;
    const copyText = `${chat.answer}\n\nRequest ID: ${chat.request_id}\nTrace ID: ${chat.trace_id}`;
    try {
      await navigator.clipboard.writeText(copyText);
      setCopyState("Saved to clipboard");
    } catch {
      setCopyState("Copy unavailable");
    }
  }

  async function rerunCurrentWorkflow() {
    if (!chat || !lastQuestion) return;
    await runChat(lastQuestion, lastEmployeeId, { useCase: lastUseCase, attachment: lastAttachment });
  }

  async function draftPeopleOpsEmail() {
    if (!chat || chat.workflow !== "remote_work" || !lastQuestion) return;
    await runChat(
      `${lastQuestion} Draft a PeopleOps follow-up email for this request.`,
      lastEmployeeId,
      { useCase: lastUseCase, attachment: lastAttachment },
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
        useCase: lastUseCase,
        attachment: lastAttachment,
      });
    } catch (error) {
      setChatError(error instanceof Error ? error.message : "Confirmation could not be completed.");
    } finally {
      setConfirming(false);
    }
  }

  function selectUseCase(value: UseCase) {
    setUseCase(value);
    const option = useCaseOptions.find((item) => item.value === value);
    if (!message.trim() && option?.starter) setMessage(option.starter);
  }

  async function attachFile(file: File) {
    setAttachmentError("");
    const mediaType = attachmentMediaType(file);
    if (!mediaType) {
      setAttachment(null);
      setAttachmentError("Choose a TXT, Markdown, or PDF file.");
      return;
    }
    if (file.size > 2_000_000) {
      setAttachment(null);
      setAttachmentError("Attachments must be 2 MB or smaller.");
      return;
    }

    setAttachmentLoading(true);
    try {
      const response = await fetch("/attachments/extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: file.name,
          media_type: mediaType,
          content_base64: await fileToBase64(file),
        }),
      });
      if (!response.ok) throw new Error(await responseError(response));
      setAttachment((await response.json()) as AttachmentContext);
    } catch (error) {
      setAttachment(null);
      setAttachmentError(error instanceof Error ? error.message : "The attachment could not be read.");
    } finally {
      setAttachmentLoading(false);
    }
  }

  function removeAttachment() {
    setAttachment(null);
    setAttachmentError("");
    if (attachmentInputRef.current) attachmentInputRef.current.value = "";
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
          <select ref={employeeSelectRef} value={employeeId} onChange={(event) => setEmployeeId(event.target.value)}>
            {employees.map((employee) => (
              <option value={employee.id} key={employee.id}>{employee.name} ({employee.id})</option>
            ))}
          </select>
        </label>
      </header>

      <div className="workspace">
        <aside className="left-rail" aria-label="Workspace navigation and demo tasks">
          <nav className="workspace-nav" aria-label="Workspace navigation">
            <a className="active" href="#chat-workspace"><NavIcon name="chat" />Chat</a>
            <button type="button" onClick={() => setDemoTasksOpen((open) => !open)} aria-expanded={demoTasksOpen} aria-controls="demo-tasks">
              <NavIcon name="tasks" /><span>Demo Tasks</span><span className="nav-chevron" aria-hidden="true">⌄</span>
            </button>
            <a href={chat ? "#request-details" : "#chat-workspace"}><NavIcon name="requests" />My Requests</a>
            <a href="#employee-context"><NavIcon name="profile" />My Profile</a>
            <a href="#pto-balance"><NavIcon name="calendar" />PTO Balance</a>
            <a href="#benefits"><NavIcon name="benefits" />Benefits</a>
            <a href="#composer-help"><NavIcon name="help" />Help</a>
            <button type="button" onClick={() => employeeSelectRef.current?.focus()}><NavIcon name="settings" /><span>Settings</span></button>
          </nav>

          {demoTasksOpen && <section id="demo-tasks" className="rail-section" aria-labelledby="demo-tasks-title">
            <div className="rail-heading">
              <h2 id="demo-tasks-title">Demo tasks</h2>
              <span>{demoTasks.length}</span>
            </div>
            <div className="task-list">
              {demoTasks.map((task) => (
                <article className="task-card" key={task.id}>
                  <div className="task-title"><span>{task.number}</span><strong>{task.title}</strong></div>
                  <dl>
                    <div><dt>Employee</dt><dd>{task.employeeId ?? "Not used"}</dd></div>
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
          </section>}

          <section id="system-health" className="rail-section health-section" aria-labelledby="health-title" aria-live="polite">
            <div className="rail-heading">
              <div className="health-title-line">
                <h2 id="health-title">System health</h2>
                <a className="health-endpoint" href="/health" target="_blank" rel="noreferrer">/health</a>
              </div>
              <button type="button" onClick={() => void refreshHealth()} disabled={healthLoading}>
                {healthLoading ? "Checking" : "Refresh"}
              </button>
            </div>
            {healthError ? (
              <p className="health-error" role="alert">{healthError}</p>
            ) : healthLoading && !health ? (
              <p className="health-loading">Checking service health…</p>
            ) : (
              <ul className="health-list">
                {primaryHealthComponents.map(({ key, label }) => {
                  const component = health?.components[key];
                  const status = component?.status ?? "error";
                  return (
                    <li key={key} title={component?.detail ?? `${label} status is unavailable.`}>
                      <span className={`health-dot ${status}`} aria-hidden="true" />
                      <span>{label}</span>
                      <strong className={`health-status ${status}`}>{healthStatusLabel(status)}</strong>
                    </li>
                  );
                })}
              </ul>
            )}
            {health && (
              <dl className="health-meta">
                <div><dt>App Version</dt><dd>v{health.version} · {health.environment}</dd></div>
                <div>
                  <dt>Last checked</dt>
                  <dd>{healthCheckedAt ? <time dateTime={healthCheckedAt.toISOString()}>{healthCheckedLabel(healthCheckedAt)}</time> : "—"}</dd>
                </div>
                <div><dt>Release</dt><dd>{health.release_sha.slice(0, 7)}</dd></div>
              </dl>
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
                <span className="avatar small" aria-hidden="true">{lastEmployee ? lastEmployee.name.charAt(0) : "P"}</span>
                <div>
                  <div className="message-author"><strong>You</strong><span>{lastEmployee?.id ?? "General policy"}</span></div>
                  <p>{lastQuestion}</p>
                  {lastAttachment && <span className="user-attachment">▤ {lastAttachment.filename}</span>}
                </div>
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

                    <GuidanceSection answer={chat.answer} decisionSummary={chat.decision_summary} />

                    {chat.decision_summary?.next_steps.length ? (
                      <section className="next-steps" aria-labelledby="next-steps-title">
                        <h3 id="next-steps-title">Next steps</h3>
                        <ol>{chat.decision_summary.next_steps.map((step) => <li key={step}>{step}</li>)}</ol>
                      </section>
                    ) : null}
                  </section>

                  <section id="request-details" className="source-action-panel" aria-labelledby="source-summary-title">
                    <div className="source-summary-heading">
                      <div>
                        <h3 id="source-summary-title">Summary based on Northstar policies</h3>
                        <span>{chat.citations.length} {chat.citations.length === 1 ? "source" : "sources"}</span>
                      </div>
                      <a href="#citations-panel">View evidence</a>
                    </div>
                    <div className="source-strip" aria-label="Cited policy sections">
                      {chat.citations.map((citation) => (
                        <a href={`#citation-${citation.chunk_id}`} title={citation.title} key={citation.chunk_id}>
                          <span className="source-document" aria-hidden="true">▤</span>
                          <span><small>{citation.policy_id}</small><strong>§ {citation.section_id}</strong></span>
                        </a>
                      ))}
                      {chat.citations.length === 0 && <span className="no-sources">No citations returned for this controlled response.</span>}
                    </div>

                    <div className="response-actions" aria-label="Available next actions">
                      {chat.workflow === "remote_work" && chat.outcome === "conditional" && (
                        <ActionButton icon="✉" title="Draft PeopleOps email" subtitle="available next action" onClick={() => void draftPeopleOpsEmail()} />
                      )}
                      {["policy", "remote_work", "pto", "expense"].includes(chat.workflow) && (
                        <ActionButton
                          icon="↻"
                          title={chat.workflow === "remote_work" ? "Check my eligibility" : `Recheck ${workflowTitle(chat.workflow).toLowerCase()}`}
                          subtitle="run the verified workflow again"
                          onClick={() => void rerunCurrentWorkflow()}
                        />
                      )}
                      {chat.pending_action && (
                        <ActionButton icon="□" title="Review mock request" subtitle="confirmation required" onClick={() => setConfirmationOpen(true)} primary />
                      )}
                      <ActionButton icon="▣" title={copyState} subtitle="copy answer and audit IDs" onClick={() => void copyGuidance()} />
                      <ActionButton icon="＋" title="New question" subtitle="start a fresh conversation" onClick={startNewChat} />
                    </div>
                  </section>
                </div>
              </article>
            )}
          </section>

          <form id="composer-help" className="composer" onSubmit={submitQuestion}>
            <label className="sr-only" htmlFor="question">Ask a follow-up or start another workflow</label>
            <div className="composer-row">
              <textarea
                id="question"
                rows={2}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Ask a follow-up question…"
                aria-describedby="composer-context attachment-status"
              />
              <button className="send-button" disabled={submitting || confirming || attachmentLoading || !message.trim()} type="submit">
                <span className="sr-only">Send question</span><span aria-hidden="true">➤</span>
              </button>
            </div>
            <div className="composer-toolbar">
              <input
                ref={attachmentInputRef}
                className="sr-only"
                id="attachment-input"
                type="file"
                accept=".txt,.md,.pdf,text/plain,text/markdown,application/pdf"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void attachFile(file);
                }}
              />
              <button className="attach-button" type="button" onClick={() => attachmentInputRef.current?.click()} disabled={attachmentLoading}>
                <span aria-hidden="true">⌕</span>{attachmentLoading ? "Reading file…" : "Attach file"}
              </button>
              <label className="use-case-select" htmlFor="use-case">
                <span>Use case:</span>
                <select id="use-case" value={useCase} onChange={(event) => selectUseCase(event.target.value as UseCase)}>
                  {useCaseOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
              </label>
              <span id="composer-context" className="composer-context" title="Synthetic employee and fixed demo policy date">
                {selectedEmployee.id} · as of 2026-09-01
              </span>
            </div>
            <div id="attachment-status" aria-live="polite">
              {attachment && (
                <div className="attachment-chip">
                  <span aria-hidden="true">▤</span>
                  <span><strong>{attachment.filename}</strong><small>{Math.ceil(attachment.original_size_bytes / 1024)} KB · extracted{attachment.truncated ? " · shortened to 6,000 characters" : ""}</small></span>
                  <button type="button" aria-label={`Remove ${attachment.filename}`} onClick={removeAttachment}>×</button>
                </div>
              )}
              {attachmentError && <p className="attachment-error" role="alert">{attachmentError}</p>}
            </div>
          </form>
          <p className="assistant-disclaimer">PeopleOps Assistant can make mistakes. Review citations and verify guidance before acting.</p>

          <section id="employee-context" className="context-panel" aria-labelledby="context-title">
            <div className="context-heading"><div><p className="section-kicker">Selected employee</p><h2 id="context-title">Context</h2></div><span>{selectedEmployee.id}</span></div>
            <div className="context-grid">
              <article><span aria-hidden="true">○</span><div><small>Employee</small><strong>{selectedEmployee.name}</strong><p>{selectedEmployee.role}<br />{selectedEmployee.department}</p></div></article>
              <article id="pto-balance"><span aria-hidden="true">□</span><div><small>PTO balance</small><strong>{selectedEmployee.ptoDays} days</strong><p>Available on demo policy date</p></div></article>
              <article id="benefits"><span aria-hidden="true">♡</span><div><small>Benefits</small><strong>{selectedEmployee.benefits}</strong><p>Synthetic status as of the demo date</p></div></article>
              <article><span aria-hidden="true">◇</span><div><small>Manager</small><strong>{selectedEmployee.manager}</strong><p>Current reporting line</p></div></article>
              <article><span aria-hidden="true">⌖</span><div><small>Home office</small><strong>{selectedEmployee.location}</strong><p>Registered location</p></div></article>
              <article><span aria-hidden="true">▣</span><div><small>Employment</small><strong>{selectedEmployee.employment}</strong><p>Active synthetic record</p></div></article>
            </div>
          </section>
        </main>

        <aside className="evidence-rail" aria-label="Citations and operational evidence">
          <details id="citations-panel" className="inspector-panel" open>
            <summary><span>Citations <strong>({chat?.citations.length ?? 0})</strong></span><span aria-hidden="true">⌃</span></summary>
            <div className="citation-list">
              {chat?.citations.map((citation, index) => (
                <article id={`citation-${citation.chunk_id}`} className="citation-item" key={citation.chunk_id}>
                  <span className="citation-number">{index + 1}</span>
                  <div>
                    <div className="citation-meta"><strong>{citation.policy_id}</strong><span>v{citation.version}</span><span>{citation.source_format.toUpperCase()}</span></div>
                    <h2>{citation.title}</h2>
                    <blockquote className="citation-snippet">
                      <strong>§ {citation.section_id}</strong>
                      <span>{readableCitationSnippet(citation.snippet)}</span>
                    </blockquote>
                    <small>Effective {citation.effective_date}{citation.page ? ` · page ${citation.page}` : ""} · score {citation.retrieval_score.toFixed(3)}</small>
                    <details className="full-snippet"><summary>View complete excerpt</summary><p>{citation.snippet}</p></details>
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
            {chat && (
              <div className="trace-evidence">
                <div className="trace-footer">
                  <span>{chat.citations.length} cited sections</span>
                  <span>{chat.tool_trace.length} MCP operations</span>
                  <span>{chat.generation.mode === "provider" ? `${chat.generation.duration_ms} ms synthesis` : `${totalTraceDuration} ms tool time`}</span>
                </div>
                <details className="technical-details">
                  <summary>Technical details</summary>
                  <dl>
                    <div><dt>Request ID</dt><dd>{chat.request_id}</dd></div>
                    <div><dt>Trace ID</dt><dd>{chat.trace_id}</dd></div>
                    <div><dt>Generation</dt><dd>{chat.generation.mode} · {chat.generation.provider}</dd></div>
                  </dl>
                </details>
              </div>
            )}
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
