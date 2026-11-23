import { NextRequest, NextResponse } from "next/server";
import { coreApi } from "@/lib/api-server";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const category = searchParams.get("category") || undefined;
  const limit = parseInt(searchParams.get("limit") || "50", 10);
  const offset = parseInt(searchParams.get("offset") || "0", 10);

  const { data, error, status } = await coreApi.getAccountActivity(category, limit, offset);
  if (error) {
    return NextResponse.json({ error }, { status });
  }
  return NextResponse.json(data);
}
