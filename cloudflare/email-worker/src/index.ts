import PostalMime from "postal-mime";

interface Env {
  BACKEND_URL: string;
  INBOUND_WEBHOOK_SECRET: string;
  ALLOWED_BANK_SENDER_DOMAINS: string;
  MAX_EMAIL_BYTES?: string;
  MAX_ATTACHMENT_BYTES?: string;
}

interface ParsedHeader {
  key: string;
  value: string;
}

function normalizeAddress(value: string): string {
  return value.trim().replace(/^.*<([^>]+)>.*$/, "$1").toLowerCase();
}

function senderDomain(address: string): string {
  const normalized = normalizeAddress(address);
  const at = normalized.lastIndexOf("@");
  return at >= 0 ? normalized.slice(at + 1) : "";
}

function isAllowedSender(sender: string, configured: string): boolean {
  const domain = senderDomain(sender);
  const allowed = configured.split(",").map((item) => item.trim().toLowerCase()).filter(Boolean);
  return Boolean(domain && allowed.some((candidate) => domain === candidate || domain.endsWith("." + candidate)));
}

function headerValue(headers: ParsedHeader[], name: string): string {
  return headers.find((header) => header.key.toLowerCase() === name.toLowerCase())?.value ?? "";
}

async function readBounded(stream: ReadableStream<Uint8Array>, maxBytes: number): Promise<Uint8Array> {
  const reader = stream.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > maxBytes) {
        await reader.cancel("Email exceeds configured size limit");
        throw new Error("EMAIL_TOO_LARGE");
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const output = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    output.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return output;
}

export default {
  async email(message: ForwardableEmailMessage, env: Env): Promise<void> {
    if (!env.BACKEND_URL || !env.INBOUND_WEBHOOK_SECRET || !env.ALLOWED_BANK_SENDER_DOMAINS) {
      message.setReject("Bank alert intake is temporarily unavailable.");
      return;
    }

    const maxBytes = Math.max(1024, Number(env.MAX_EMAIL_BYTES || 10 * 1024 * 1024));
    let raw: Uint8Array;
    try {
      raw = await readBounded(message.raw, maxBytes);
    } catch {
      message.setReject("This email is larger than IPÌLẸ̀ can accept.");
      return;
    }

    let parsed;
    try {
      parsed = await new PostalMime().parse(raw);
    } catch {
      message.setReject("IPÌLẸ̀ could not read this email. Please forward the original bank alert.");
      return;
    }

    const sender = normalizeAddress(message.from);
    if (!isAllowedSender(sender, env.ALLOWED_BANK_SENDER_DOMAINS)) {
      message.setReject("This sender is not on IPÌLẸ̀'s approved bank-alert list.");
      return;
    }

    const recipient = normalizeAddress(message.to);
    if (!/^bank-alert\+[a-z0-9_-]{32,}@[^@]+$/i.test(recipient)) {
      message.setReject("This household import address is invalid or expired.");
      return;
    }

    const headers: ParsedHeader[] = (parsed.headers ?? []).map((header) => ({
      key: header.key,
      value: header.value,
    }));
    // Cloudflare prepends its trusted result to message.headers. Never trust
    // Authentication-Results parsed from raw MIME: a sender can forge that header.
    const authenticationResults = (message.headers.get("Authentication-Results") ?? "").toLowerCase();
    const authenticated =
      /^\s*mx\.cloudflare\.net\s*;/.test(authenticationResults) &&
      /\bdmarc=pass\b/.test(authenticationResults);
    if (!authenticated) {
      message.setReject("The sender could not be verified. Contact your bank or forward an original alert.");
      return;
    }

    const maxAttachmentBytes = Math.max(0, Number(env.MAX_ATTACHMENT_BYTES || 10 * 1024 * 1024));
    const attachments = (parsed.attachments ?? []).map((attachment) => ({
      filename: (attachment.filename || "attachment").slice(0, 180),
      content_type: (attachment.mimeType || "application/octet-stream").slice(0, 120),
      size: typeof attachment.content === "string"
        ? new TextEncoder().encode(attachment.content).byteLength
        : attachment.content?.byteLength ?? 0,
    }));
    if (attachments.some((attachment) => attachment.size > maxAttachmentBytes)) {
      message.setReject("An email attachment exceeds IPÌLẸ̀'s file-size limit.");
      return;
    }

    const payload = {
      To: recipient,
      From: sender,
      Subject: (parsed.subject || "Bank transaction alert").slice(0, 200),
      TextBody: (parsed.text || "").slice(0, 100_000),
      HtmlBody: parsed.html ? String(parsed.html).slice(0, 200_000) : "",
      Date: message.headers.get("Date") ?? headerValue(headers, "date"),
      MessageID: message.headers.get("Message-ID") ?? headerValue(headers, "message-id"),
      AuthenticationResults: authenticationResults,
      Attachments: attachments,
      AttachmentPolicy: attachments.length ? "manual_upload_required" : "none",
      Provider: "cloudflare-email-routing",
    };

    let response: Response;
    try {
      response = await fetch(new URL("/api/v1/imports/inbound-email", env.BACKEND_URL), {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-inbound-email-secret": env.INBOUND_WEBHOOK_SECRET,
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(12_000),
      });
    } catch {
      message.setReject("IPÌLẸ̀ could not receive this alert right now. Please try forwarding it again later.");
      return;
    }

    if (response.ok) return;
    if (response.status >= 400 && response.status < 500) {
      message.setReject("IPÌLẸ̀ could not accept this alert. Check the household import address and sender.");
      return;
    }
    message.setReject("IPÌLẸ̀ is temporarily unavailable. Please try forwarding this alert again later.");
  },
} satisfies ExportedHandler<Env>;
