import { NextResponse } from "next/server";

export async function POST() {
  return NextResponse.json({
    access_token: "ekb-public-access",
    token_type: "bearer",
    expires_in: 86400,
  });
}
