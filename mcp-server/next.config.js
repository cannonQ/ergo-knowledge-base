/** @type {import('next').NextConfig} */
const nextConfig = {
  // Include content dir in the serverless function bundle
  // (lives outside mcp-server/ in the repo root)
  outputFileTracingIncludes: {
    "/api/mcp": ["../content/**/*"],
  },
};

module.exports = nextConfig;
