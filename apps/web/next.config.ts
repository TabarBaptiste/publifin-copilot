import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker image: .next/standalone holds a minimal server and only the files it needs.
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
};

export default nextConfig;
