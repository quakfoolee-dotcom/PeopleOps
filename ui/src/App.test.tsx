import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const healthPayload = {
  status: "ok",
  app_name: "PeopleOps Assistant",
  version: "0.5.1",
  environment: "test",
  components: {
    application: { status: "ready", detail: "FastAPI is serving requests." },
    policy_corpus: { status: "ready", detail: "12 synthetic policies validated." },
    rag_index: { status: "ready", detail: "169 sections indexed." },
    mcp: { status: "ready", detail: "8 tools serve the Phase 8 interface." },
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
  pending_action: {
    action_type: "create_mock_hr_ticket",
    confirmation_id: "PREVIEW-ABCDEF0123456789",
    expires_at: "2026-09-01T12:05:00Z",
    summary: "Create a high-priority synthetic HR case for E-1011.",
    sanitized_arguments: { employee_id: "E-1011", priority: "high" },
    confirmation_required: true,
  },
};

const createdPayload = {
  ...previewPayload,
  trace_id: "19928d70-989a-4c5e-b603-9d99fa5be544",
  status: "completed",
  outcome: "answered",
  answer: "Created synthetic ticket TKT-9001.",
  pending_action: null,
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
    expect(screen.getAllByText("Alex Morgan").length).toBeGreaterThan(0);
    expect(await screen.findByText("v0.5.1 · test · ok")).toBeInTheDocument();
    expect(screen.getAllByText(/Citations/i).length).toBeGreaterThan(0);
    expect(screen.getByText("Tool trace", { exact: false })).toBeInTheDocument();
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

  it("runs a cited workflow and exposes sources, trace, and both identifiers", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => healthPayload })
      .mockResolvedValueOnce({ ok: true, json: async () => chatPayload });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Send question" }));

    expect(await screen.findByText(/not automatically approved/i)).toBeInTheDocument();
    expect(screen.getAllByText(/INT-5/).length).toBeGreaterThan(0);
    expect(screen.getByText("Full cited snippet")).toBeInTheDocument();
    expect(screen.getByText("mcp discover tools")).toBeInTheDocument();
    expect(screen.getByText(chatPayload.request_id)).toBeInTheDocument();
    expect(screen.getByText(chatPayload.trace_id)).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/chat",
      expect.objectContaining({ method: "POST" }),
    );
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
    expect(confirmButton).toHaveFocus();
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
