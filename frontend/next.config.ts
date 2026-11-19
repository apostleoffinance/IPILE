import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // OpenNext owns the deployment output for Cloudflare Workers.
  // Keep the backend rewrite so Vercel remains a valid rollback target.
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL;
    if (!backendUrl) return [];

    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendUrl.replace(/\/$/, "")}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
