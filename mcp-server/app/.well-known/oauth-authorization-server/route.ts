import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const origin = req.headers.get("x-forwarded-host")
    ? `https://${req.headers.get("x-forwarded-host")}`
    : new URL(req.url).origin;

  return NextResponse.json({
    issuer: origin,
    authorization_endpoint: `${origin}/api/authorize`,
    token_endpoint: `${origin}/api/token`,
    response_types_supported: ["code"],
    grant_types_supported: ["authorization_code"],
    code_challenge_methods_supported: ["S256"],
  });
}
