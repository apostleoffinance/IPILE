import assert from "node:assert/strict";
import { api } from "./api";

async function main() {
  const originalFetch = globalThis.fetch;
  const requested: string[] = [];

  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = String(input);
    requested.push(url);
    if (url.endsWith("/api/v1/auth/me")) {
      return new Response(JSON.stringify({
        id: "user-1",
        email: "owner@example.com",
        display_name: "Household Owner",
        status: "active",
      }), { status: 200, headers: { "content-type": "application/json" } });
    }
    if (url.endsWith("/api/v1/members")) {
      return new Response(JSON.stringify([
        {
          id: "member-other",
          household_id: "household-1",
          user_id: "user-2",
          display_name: "Other member",
          role: "member",
          relationship: "sibling",
          member_type: "adult",
          is_financial_contributor: false,
          permissions: { view_all_contributions: false, view_all_obligations: false },
        },
        {
          id: "member-current",
          household_id: "household-1",
          user_id: "user-1",
          display_name: "Household Owner",
          role: "owner",
          relationship: "self",
          member_type: "adult",
          is_financial_contributor: true,
          permissions: { view_all_contributions: true, view_all_obligations: true },
        },
      ]), { status: 200, headers: { "content-type": "application/json" } });
    }
    throw new Error(`Unexpected API request: ${url}`);
  }) as typeof fetch;

  try {
    const member = await api.currentMember();
    assert.equal(member.id, "member-current");
    assert.equal(member.role, "owner");
    assert.ok(requested.some((url) => url.endsWith("/api/v1/auth/me")));
    assert.ok(requested.some((url) => url.endsWith("/api/v1/members")));
    assert.ok(!requested.some((url) => url.endsWith("/api/v1/members/me")));
  } finally {
    globalThis.fetch = originalFetch;
  }
}

void main().then(() => console.log("currentMember compatibility test passed"));
