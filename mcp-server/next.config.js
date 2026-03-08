/** @type {import('next').NextConfig} */
const nextConfig = {
  // Exclude LanceDB's native binary from webpack bundling
  webpack: (config) => {
    config.externals.push({ "@lancedb/lancedb": "@lancedb/lancedb" });
    return config;
  },
  serverExternalPackages: ["@lancedb/lancedb"],
  // Include vectordb + content dirs in the serverless function bundle
  // These live outside mcp-server/ in the repo root
  outputFileTracingIncludes: {
    "/api/mcp": ["../vectordb/**/*", "../content/**/*"],
  },
};

module.exports = nextConfig;
