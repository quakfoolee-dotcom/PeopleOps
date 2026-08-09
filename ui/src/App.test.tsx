import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const healthPayload = {
  status: "ok",
  app_name: "PeopleOps Assistant",
  version: "1.0.0",
  environment: "test",
  release_sha: "test-release-sha",
  components: {
    application: { status: "ready", detail: "FastAPI is serving requests." },
    policy_corpus: { status: "ready", detail: "12 synthetic policies validated." },
    rag_index: { status: "ready", detail: "169 sections indexed." },
    mcp: { status: "ready", detail: "8 tools serve the Phase 8 interface." },
    mock_database: { status: "ready", detail: "30 synthetic employee records validated." },
    llm_provider: { status: "ready", detail: "Deterministic test provider is ready." },
  },
};

const citation = {
  policy_id: "POL-INT-001",
  section_id: "INT-5",
  title: "International Work — Duration categories",
  snippet: "International exceptional requests require 30 business days of notice.",
  version: "1.0",
  effective_date: "2026-09-01",
  source_format: "markdown",
  source_path: "policy_corpus/runtime_corpus/POL-INT-001.md",
  page: null,
  chunk_id: "POL-INT-001::INT-5::01",
  retrieval_score: 0.91,
};

const policyCitation = {
  ...citation,
  policy_id: "POL-BEN-001",
  section_id: "BEN-5",
  title: "Employee Benefits Eligibility — Enrollment and changes",
  snippet: "A newly eligible employee has 31 calendar days to complete enrollment or waiver elections.",
  source_path: "policy_corpus/runtime_corpus/POL-BEN-001.md",
  chunk_id: "POL-BEN-001::BEN-5::01",
  retrieval_score: 0.95,
};

const traceEntry = {
  sequence: 1,
  tool_name: "mcp_discover_tools",
  sanitized_arguments: {},
  status: "succeeded",
  result_summary: "Discovered 8 tools.",
  duration_ms: 2,
  error_code: null,
};

const chatPayload = {
  request_id: "89928d70-989a-4c5e-b603-9d99fa5be566",
  trace_id: "39928d70-989a-4c5e-b603-9d99fa5be511",
  as_of_date: "2026-09-01",
  status: "completed",
  outcome: "conditional",
  answer: "Conditional guidance — this request is not automatically approved.",
  workflow: "remote_work",
  workflow_state: "respond",
  citations: [citation],
  tool_trace: [traceEntry],
  decision_summary: {
    status_label: "Conditionally eligible",
    duration_label: "42 calendar days / 30 business days",
    category_label: "International exceptional",
    required_approvals: ["Manager", "People Operations", "Security", "Legal"],
    clarification_needed: ["Exact travel and working dates"],
    next_steps: [
      "Provide exact travel and working dates.",
      "Obtain all required reviews.",
    ],
  },
  generation: {
    mode: "provider",
    provider: "openrouter",
    model: "openrouter/free",
    resolved_model: "nvidia/example:free",
    duration_ms: 240,
    detail: "Provider output passed the grounding gate.",
  },
  pending_action: null,
};

const previewPayload = {
  ...chatPayload,
  request_id: "79928d70-989a-4c5e-b603-9d99fa5be522",
  trace_id: "29928d70-989a-4c5e-b603-9d99fa5be533",
  status: "awaiting_confirmation",
  outcome: "confirmation_required",
  answer: "Review the synthetic ticket preview before creation.",
  workflow: "mock_ticket",
  workflow_state: "respond",
  citations: [],
  tool_trace: [traceEntry],
  decision_summary: {
    status_label: "Confirmation required",
    duration_label: "Synthetic preview only",
    category_label: "Workplace concern",
    required_approvals: ["Explicit user confirmation"],
    clarification_needed: [],
    next_steps: ["Review the sanitized request preview.", "Confirm or cancel the mock action."],
  },
  pending_action: {
    action_type: "create_mock_hr_ticket",
    confirmation_id: "PREVIEW-ABCDEF0123456789",
    expires_at: "2026-09-01T12:05:00Z",
    summary: "Create a high-priority synthetic HR case for E-1011.",
    sanitized_arguments: { employee_id: "E-1011", priority: "high" },
    confirmation_required: true,
  },
};

const draftPayload = {
  ...chatPayload,
  outcome: "draft_only",
  answer: "Draft - not sent\nSubject: People Operations follow-up\n\nPlease review this request.",
  tool_trace: [
    traceEntry,
    { ...traceEntry, sequence: 2, tool_name: "draft_hr_email", result_summary: "Created Draft - not sent." },
  ],
};

const policyPayload = {
  ...chatPayload,
  request_id: "69928d70-989a-4c5e-b603-9d99fa5be577",
  trace_id: "59928d70-989a-4c5e-b603-9d99fa5be588",
  outcome: "answered",
  answer:
    "A newly eligible employee has 31 calendar days after the eligibility notice to complete enrollment or waiver elections.",
  workflow: "policy",
  citations: [policyCitation],
  tool_trace: [
    traceEntry,
    {
      ...traceEntry,
      sequence: 2,
      tool_name: "search_policy_documents",
      result_summary: "Returned the benefits enrollment policy evidence.",
    },
    {
      ...traceEntry,
      sequence: 3,
      tool_name: "get_policy_section",
      result_summary: "Retrieved POL-BEN-001 BEN-5.",
    },
  ],
  decision_summary: {
    status_label: "Policy guidance ready",
    duration_label: null,
    category_label: "Benefits enrollment",
    required_approvals: [],
    clarification_needed: [],
    next_steps: ["Complete enrollment or waiver elections within the applicable window."],
  },
};

const createdPayload = {
  ...previewPayload,
  trace_id: "19928d70-989a-4c5e-b603-9d99fa5be544",
  status: "completed",
  outcome: "answered",
  answer: "Created synthetic ticket TKT-9001.",
  pending_action: null,
  decision_summary: {
    status_label: "Mock request created",
    duration_label: "In-memory demo record",
    category_label: "Workplace concern",
    required_approvals: ["Explicit user confirmation recorded"],
    clarification_needed: [],
    next_steps: ["Review synthetic ticket TKT-9001 in the demo trace."],
  },
  tool_trace: [
    traceEntry,
    {
      ...traceEntry,
      sequence: 2,
      tool_name: "create_mock_hr_ticket",
      result_summary: "Created TKT-9001.",
    },
  ],
};

describe("PeopleOps Assistant Phase 8 evidence-first interface", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("renders the approved workspace with live health and synthetic context", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => healthPayload }),
    );

    render(<App />);

    expect(screen.getByText("Synthetic demo environment")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Chat with PeopleOps Assistant" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Demo tasks" })).toBeInTheDocument();
    expect(screen.getByText("International remote work")).toBeInTheDocument();
    const taskRegion = screen.getByRole("region", { name: "Demo tasks" });
    expect(within(taskRegion).getByText("5")).toBeInTheDocument();
    expect(within(taskRegion).getByText("Policy and benefits guidance")).toBeInTheDocument();
    expect(screen.getAllByText("Alex Morgan").length).toBeGreaterThan(0);
    const healthRegion = await screen.findByRole("region", { name: "System health" });
    expect(within(healthRegion).getByText("MCP Connectivity")).toBeInTheDocument();
    expect(within(healthRegion).getByText("RAG Index")).toBeInTheDocument();
    expect(within(healthRegion).getByText("Mock Database")).toBeInTheDocument();
    expect(within(healthRegion).getByText("LLM Provider")).toBeInTheDocument();
    expect(within(healthRegion).getAllByText("Healthy")).toHaveLength(4);
    expect(within(healthRegion).queryByText("Application")).not.toBeInTheDocument();
    expect(within(healthRegion).queryByText("Policy Corpus")).not.toBeInTheDocument();
    expect(within(healthRegion).getByText("App Version")).toBeInTheDocument();
    expect(within(healthRegion).getByText("v1.0.0 · test")).toBeInTheDocument();
    expect(within(healthRegion).getByText("Last checked")).toBeInTheDocument();
    expect(within(healthRegion).getByText("Release")).toBeInTheDocument();
    expect(within(healthRegion).getByText("test-re")).toBeInTheDocument();
    expect(within(healthRegion).getByRole("link", { name: "/health" })).toHaveAttribute("href", "/health");
    expect(screen.getAllByText(/Citations/i).length).toBeGreaterThan(0);
    expect(screen.getByText("Tool trace", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("LLM Provider", { exact: true })).toBeInTheDocument();
  });

  it("loads a demo task and updates the selected employee context", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => healthPayload }),
    );
    render(<App />);

    const ptoCard = screen.getByText("PTO request guidance").closest("article");
    expect(ptoCard).not.toBeNull();
    fireEvent.click(within(ptoCard!).getByRole("button", { name: "Load" }));

    expect(screen.getByDisplayValue(/September 21 through September 23/i)).toBeInTheDocument();
    expect(screen.getAllByText("E-1021").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Logan Murphy").length).toBeGreaterThan(0);
    expect(screen.getByText("12 days")).toBeInTheDocument();
  });

  it("runs the employee-neutral policy and benefits demo without employee-data tools", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => healthPayload })
      .mockResolvedValueOnce({ ok: true, json: async () => policyPayload });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    const policyCard = screen.getByText("Policy and benefits guidance").closest("article");
    expect(policyCard).not.toBeNull();
    expect(within(policyCard!).getByText("Not used")).toBeInTheDocument();
    fireEvent.click(within(policyCard!).getByRole("button", { name: "Run task" }));

    expect(await screen.findByText(/31 calendar days after the eligibility notice/i)).toBeInTheDocument();
    expect(screen.getByText("General policy")).toBeInTheDocument();
    expect(screen.getAllByText(/BEN-5/).length).toBeGreaterThan(0);
    expect(screen.getByText("search policy documents")).toBeInTheDocument();
    expect(screen.getByText("get policy section")).toBeInTheDocument();
    expect(screen.queryByText("lookup employee profile")).not.toBeInTheDocument();
    expect(screen.queryByText("lookup benefits status")).not.toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const policyBody = JSON.parse(String(fetchMock.mock.calls[1][1]?.body));
    expect(policyBody.message).toMatch(/newly eligible employee/i);
    expect(policyBody).not.toHaveProperty("employee_id");
  });

  it("runs a cited workflow and exposes sources, trace, and both identifiers", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => healthPayload })
      .mockResolvedValueOnce({ ok: true, json: async () => chatPayload });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Send question" }));

    expect(await screen.findByText(/not automatically approved/i)).toBeInTheDocument();
    expect(screen.getByText("42 calendar days / 30 business days")).toBeInTheDocument();
    expect(screen.getByText("International exceptional")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Required approvals" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Clarification needed" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Next steps" })).toBeInTheDocument();
    expect(screen.getByText("Guidance complete")).toBeInTheDocument();
    expect(screen.getAllByText(/INT-5/).length).toBeGreaterThan(0);
    expect(screen.getByText("Full cited snippet")).toBeInTheDocument();
    expect(screen.getByText("mcp discover tools")).toBeInTheDocument();
    expect(screen.getByText(chatPayload.request_id)).toBeInTheDocument();
    expect(screen.getByText(chatPayload.trace_id)).toBeInTheDocument();
    expect(screen.getByText(/openrouter · nvidia\/example:free/i)).toBeInTheDocument();
    expect(screen.getByText("240 ms")).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/chat",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("runs the real remote-work email-draft action through chat", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => healthPayload })
      .mockResolvedValueOnce({ ok: true, json: async () => chatPayload })
      .mockResolvedValueOnce({ ok: true, json: async () => draftPayload });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Send question" }));
    const draftButton = await screen.findByRole("button", { name: "Draft PeopleOps email" });
    fireEvent.click(draftButton);

    expect(await screen.findByText("Draft prepared · not sent")).toBeInTheDocument();
    expect(screen.getByText(/People Operations follow-up/i)).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    const draftBody = JSON.parse(String(fetchMock.mock.calls[2][1]?.body));
    expect(draftBody.employee_id).toBe("E-1007");
    expect(draftBody.message).toMatch(/Draft a PeopleOps follow-up email/i);
  });

  it("requires confirmation before creating a mock ticket and reuses the request id", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => healthPayload })
      .mockResolvedValueOnce({ ok: true, json: async () => previewPayload })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          confirmation_id: previewPayload.pending_action.confirmation_id,
          confirmation_token: "signed-confirmation-token-that-is-never-rendered",
          synthetic_only: true,
        }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => createdPayload });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    const ticketCard = screen.getByText("Confirmation-gated ticket").closest("article");
    expect(ticketCard).not.toBeNull();
    fireEvent.click(within(ticketCard!).getByRole("button", { name: "Run task" }));

    const dialog = await screen.findByRole("dialog", { name: "Create mock HR ticket?" });
    expect(within(dialog).getByText(/No production HR system/i)).toBeInTheDocument();
    expect(screen.queryByText(/signed-confirmation-token/i)).not.toBeInTheDocument();
    const confirmButton = within(dialog).getByRole("button", { name: "Confirm mock ticket" });
    await waitFor(() => expect(confirmButton).toHaveFocus());
    fireEvent.click(confirmButton);

    expect(await screen.findByText(/Created synthetic ticket TKT-9001/i)).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));

    const confirmationCall = fetchMock.mock.calls[2];
    expect(confirmationCall[0]).toBe("/actions/mock-tickets/confirm");
    expect(JSON.parse(String(confirmationCall[1]?.body))).toEqual({
      confirmation_id: previewPayload.pending_action.confirmation_id,
      user_confirmed: true,
    });
    const createCall = fetchMock.mock.calls[3];
    const createBody = JSON.parse(String(createCall[1]?.body));
    expect(createBody.request_id).toBe(previewPayload.request_id);
    expect(createBody.employee_id).toBe("E-1011");
    expect(createBody.confirmation_token).toBeDefined();
  });

  it("keeps a pending action blocked when the confirmation card is cancelled", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => healthPayload })
      .mockResolvedValueOnce({ ok: true, json: async () => previewPayload });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    const ticketCard = screen.getByText("Confirmation-gated ticket").closest("article");
    fireEvent.click(within(ticketCard!).getByRole("button", { name: "Run task" }));
    const dialog = await screen.findByRole("dialog", { name: "Create mock HR ticket?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Review pending action" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
