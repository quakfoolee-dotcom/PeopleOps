import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const healthPayload = {
  status: "ok",
  components: {
    application: { status: "ready", detail: "FastAPI is serving requests." },
    policy_corpus: { status: "ready", detail: "12 synthetic policies validated." },
    mcp: { status: "planned", detail: "Live transport is the next milestone." },
  },
};

describe("PeopleOps Assistant foundation", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows the product identity and honest milestone state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => healthPayload }),
    );

    render(<App />);

    expect(screen.getAllByText("PeopleOps Assistant").length).toBeGreaterThan(0);
    expect(screen.getByText(/Foundation · v0.1.0/i)).toBeInTheDocument();
    expect(await screen.findByText("Foundation healthy")).toBeInTheDocument();
    expect(screen.getByText("Three reproducible HR workflows")).toBeInTheDocument();
  });
});
