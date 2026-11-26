import { afterEach, describe, expect, it, vi } from "vitest";
import worker from "../src/index";

const env = {
  BACKEND_URL: "https://staging-api.example.test",
  INBOUND_WEBHOOK_SECRET: "test-secret",
  ALLOWED_BANK_SENDER_DOMAINS: "bank.example",
  MAX_EMAIL_BYTES: "1048576",
  MAX_ATTACHMENT_BYTES: "1048576",
};

function emailMessage(options: {
  from?: string;
  to?: string;
  authentication?: string;
  cloudflareAuthentication?: string;
  body?: string;
} = {}) {
  const raw = [
    `From: ${options.from ?? "alerts@bank.example"}`,
    "To: bank-alert+abcdefghijklmnopqrstuvwxyz0123456789@inbox.example.test",
    "Subject: Debit Alert",
    "Date: Sun, 15 Nov 2026 10:00:00 +0100",
    "Message-ID: <alert-001@bank.example>",
    `Authentication-Results: ${options.authentication ?? "mx.cloudflare.net; dmarc=pass"}`,
    "MIME-Version: 1.0",
    "Content-Type: text/plain; charset=utf-8",
    "",
    options.body ?? "Your account was debited NGN 5,000.00 on 15/11/2026. Ref: ABC12345",
  ].join("\\r\\n");
  const bytes = new TextEncoder().encode(raw);
  const rejects: string[] = [];
  const message = {
    from: options.from ?? "alerts@bank.example",
    to: options.to ?? "bank-alert+abcdefghijklmnopqrstuvwxyz0123456789@inbox.example.test",
    headers: new Headers({
      "Authentication-Results": options.cloudflareAuthentication ?? "mx.cloudflare.net; spf=pass; dkim=pass; dmarc=pass header.from=bank.example",
      Date: "Sun, 15 Nov 2026 10:00:00 +0100",
      "Message-ID": "<alert-001@bank.example>",
    }),
    raw: new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(bytes);
        controller.close();
      },
    }),
    setReject(reason: string) {
      rejects.push(reason);
    },
  } as unknown as ForwardableEmailMessage;
  return { message, rejects };
}

afterEach(() => vi.unstubAllGlobals());

describe("Cloudflare inbound bank-alert Worker", () => {
  it("forwards authenticated allowlisted alerts to the backend with the shared secret", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const { message, rejects } = emailMessage();

    await worker.email(message, env as never);

    expect(rejects).toEqual([]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [URL, RequestInit];
    expect(String(url)).toBe("https://staging-api.example.test/api/v1/imports/inbound-email");
    expect((init.headers as Record<string, string>)["x-inbound-email-secret"]).toBe("test-secret");
    const payload = JSON.parse(String(init.body));
    expect(payload.To).toContain("bank-alert+");
    expect(payload.From).toBe("alerts@bank.example");
    expect(payload.MessageID).toBe("<alert-001@bank.example>");
    expect(payload.Provider).toBe("cloudflare-email-routing");
  });

  it("rejects senders outside the configured bank domain allowlist", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const { message, rejects } = emailMessage({ from: "alerts@bank.example.attacker.test" });

    await worker.email(message, env as never);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(rejects).toHaveLength(1);
  });

  it("accepts the operator-observed OPay sender domain when explicitly allowlisted", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const { message, rejects } = emailMessage({ from: "no-reply@opay-nigeria.com", cloudflareAuthentication: "mx.cloudflare.net; spf=pass; dkim=pass; dmarc=pass header.from=opay-nigeria.com" });
    const opayEnv = {
      ...env,
      ALLOWED_BANK_SENDER_DOMAINS: "bank.example,opay-nigeria.com",
    };

    await worker.email(message, opayEnv as never);

    expect(rejects).toEqual([]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const payload = JSON.parse(String((fetchMock.mock.calls[0] as [URL, RequestInit])[1].body));
    expect(payload.From).toBe("no-reply@opay-nigeria.com");
  });

  it("rejects a forged raw MIME authentication header when Cloudflare does not pass DMARC", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const { message, rejects } = emailMessage({
      authentication: "mx.cloudflare.net; dmarc=pass",
      cloudflareAuthentication: "mx.cloudflare.net; dmarc=fail; dkim=fail; spf=pass",
    });

    await worker.email(message, env as never);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(rejects).toHaveLength(1);
  });

  it("rejects a passing DMARC result for a different From domain", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const { message, rejects } = emailMessage({
      cloudflareAuthentication: "mx.cloudflare.net; spf=pass; dkim=pass; dmarc=pass header.from=attacker.test",
    });

    await worker.email(message, env as never);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(rejects).toHaveLength(1);
  });

  it("rejects recipients without a household token", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const { message, rejects } = emailMessage({ to: "bank-alert@inbox.example.test" });

    await worker.email(message, env as never);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(rejects).toHaveLength(1);
  });

  it("rejects oversized email payloads before parsing or forwarding", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const { message, rejects } = emailMessage({ body: "x".repeat(2048) });
    const oversizedEnv = { ...env, MAX_EMAIL_BYTES: "1024" };

    await worker.email(message, oversizedEnv as never);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(rejects).toHaveLength(1);
  });

  it("rejects delivery when the backend is unavailable", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error("network error"));
    vi.stubGlobal("fetch", fetchMock);
    const { message, rejects } = emailMessage();

    await worker.email(message, env as never);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(rejects).toHaveLength(1);
  });
});
