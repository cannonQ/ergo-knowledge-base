/** @type {import('next').NextConfig} */
const nextConfig = {
  // Exclude LanceDB's native binary from webpack bundling
  webpack: (config) => {
    config.externals.push({ "@lancedb/lancedb": "@lancedb/lancedb" });
    return config;
  },
  // Increase serverless function timeout for vector search
  serverExternalPackages: ["@lancedb/lancedb"],
};

module.exports = nextConfig;
