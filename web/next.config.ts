import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    proxyClientMaxBodySize: 2 * 1024 * 1024 * 1024, // 2 GB — allow large video uploads
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:5050/api/:path*",
      },
    ];
  },
};

export default nextConfig;
