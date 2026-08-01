import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // standalone 产出自包含的 .next/standalone 目录，
  // 生产镜像因此不需要携带完整 node_modules。
  output: "standalone",
  // monorepo 中显式指定根目录，避免 Next 向上误判 workspace 根。
  outputFileTracingRoot: __dirname,
};

export default nextConfig;
