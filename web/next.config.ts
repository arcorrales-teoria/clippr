import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    proxyClientMaxBodySize: 2 * 1024 * 1024 * 1024, // 2 GB — allow large video uploads
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5050"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
