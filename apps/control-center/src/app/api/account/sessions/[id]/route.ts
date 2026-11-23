import { NextRequest, NextResponse } from "next/server";
import { coreApi } from "@/lib/api-server";

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const numId = parseInt(id, 10);
  if (isNaN(numId)) {
    return NextResponse.json({ error: "Invalid session id" }, { status: 400 });
  }

  const { data, error, status } = await coreApi.revokeAccountSession(numId);
  if (error) {
    return NextResponse.json({ error }, { status });
  }
  return NextResponse.json(data);
}
