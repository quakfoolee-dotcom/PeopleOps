import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const healthPayload = {
  status: "ok",
  components: {
    application: { status: "ready", detail: "FastAPI is serving requests." },
    policy_corpus: { status: "ready", detail: "12 synthetic policies validated." },
    rag_index: { status: "ready", detail: "169 sections indexed." },
    mcp: { status: "ready", detail: "2 Phase 5 tools are discoverable." },
  },
};

const chatPayload = {
  request_id: "89928d70-989a-4c5e-b603-9d99fa5be566",
  as_of_date: "2026-09-01",
  status: "completed",
  outcome: "conditional",
  answer: "Conditional guidance — this request is not automatically approved.",
  citations: [
    {
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
    },
  ],
  tool_trace: [
    {
      sequence: 1,
      tool_name: "mcp_discover_tools",
      sanitized_arguments: {},
      status: "succeeded",
      result_summary: "Discovered 2 tools.",
      duration_ms: 2,
      error_code: null,
    },
  ],
};

describe("PeopleOps Assistant Phase 5 interface", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows the product identity and live milestone state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => healthPayload }),
    );

    render(<App />);

    expect(screen.getAllByText("PeopleOps Assistant").length).toBeGreaterThan(0);
    expect(screen.getByText(/Phase 5 · v0.2.0/i)).toBeInTheDocument();
    expect(await screen.findByText("Service healthy")).toBeInTheDocument();
    expect(screen.getByText("live MCP tools")).toBeInTheDocument();
    expect(screen.getByText("Trace a request from question to evidence")).toBeInTheDocument();
  });

  it("submits the preset and renders citations and the operational trace", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => healthPayload })
      .mockResolvedValueOnce({ ok: true, json: async () => chatPayload });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Run cited workflow" }));

    expect(await screen.findByText(/not automatically approved/i)).toBeInTheDocument();
    expect(screen.getByText("INT-5")).toBeInTheDocument();
    expect(screen.getByText("mcp discover tools")).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/chat",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
