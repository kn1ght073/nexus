import { NextRequest, NextResponse } from "next/server";
import { coreApi } from "@/lib/api-server";

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const deviceId = parseInt(id, 10);
  if (isNaN(deviceId)) {
    return NextResponse.json({ error: "Invalid device id" }, { status: 400 });
  }

  const { error, status } = await coreApi.removeDevice(deviceId);
  if (error) {
    return NextResponse.json({ error }, { status });
  }
  return NextResponse.json({ ok: true });
}
