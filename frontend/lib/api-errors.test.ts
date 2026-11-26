import assert from "node:assert/strict";
import { api } from "./api";

async function main() {
  const originalFetch = globalThis.fetch;
  const requests: { url: string; init?: RequestInit }[] = [];

  try {
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      requests.push({ url, init });
      if (url.endsWith("/api/v1/auth/login")) {
        const body = JSON.parse(String(init?.body ?? "{}")) as { password?: string };
        if (body.password === "wrong-password") {
          return new Response(JSON.stringify({ detail: "Invalid credentials." }), {
            status: 401,
            headers: { "content-type": "application/json" },
          });
        }
        return new Response(JSON.stringify({
          id: "user-1",
          email: "owner@example.com",
          display_name: "Owner",
          status: "active",
        }), { status: 200, headers: { "content-type": "application/json" } });
      }
      if (url.endsWith("/api/v1/health")) {
        return new Response("<html>upstream unavailable</html>", {
          status: 503,
          headers: { "content-type": "text/html" },
        });
      }
      throw new Error(`Unexpected API request: ${url}`);
    }) as typeof fetch;

    await api.login({ email: "owner@example.com", password: "correct-password" });
    assert.equal(requests.length, 1, "login should not make a separate CSRF bootstrap request");
    assert.ok(requests[0].url.endsWith("/api/v1/auth/login"));
    assert.equal(
      (requests[0].init?.headers as Record<string, string>)["X-CSRF-Token"],
      undefined,
      "login is exempt from CSRF and should not require a token",
    );

    await assert.rejects(
      api.login({ email: "owner@example.com", password: "wrong-password" }),
      /Your email or password doesn't look right/,
    );
    assert.equal(requests.length, 2, "failed login must not trigger a CSRF bootstrap or retry");

    await assert.rejects(
      api.health(),
      (error: unknown) => {
        assert.ok(error instanceof Error);
        assert.equal(
          error.message,
          "IPÌLẸ̀ is temporarily unavailable. Please try again in a moment.",
        );
        assert.ok(!error.message.includes("upstream unavailable"));
        return true;
      },
    );

    console.log("API authentication and friendly error handling tests passed");
  } finally {
    globalThis.fetch = originalFetch;
  }
}

void main();
