import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

function backendUrl() {
  const value = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!value) throw new Error("BACKEND_URL is not configured.");
  return value.replace(/\/$/, "");
}

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const target = `${backendUrl()}/api/v1/${path.join("/")}${request.nextUrl.search}`;
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");
  headers.delete("origin");

  const body = ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer();
  const response = await fetch(target, {
    method: request.method,
    headers,
    body,
    redirect: "manual",
  });

  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");
  const setCookies = response.headers.getSetCookie?.() ?? [];
  responseHeaders.delete("set-cookie");
  for (const cookie of setCookies) responseHeaders.append("set-cookie", cookie);

  return new NextResponse(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  });
}

export const GET = proxy;
export const HEAD = proxy;
export const OPTIONS = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
