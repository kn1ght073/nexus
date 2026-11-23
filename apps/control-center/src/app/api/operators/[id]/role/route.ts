import { NextRequest, NextResponse } from "next/server";
import { coreApi } from "@/lib/api-server";

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const userId = parseInt(id, 10);
  if (isNaN(userId)) {
    return NextResponse.json({ error: "Invalid user id" }, { status: 400 });
  }

  try {
    const body = await request.json();
    const { data, error, status } = await coreApi.updateUserRole(userId, body.role);
    if (error) {
      return NextResponse.json({ error }, { status });
    }
    return NextResponse.json(data);
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Invalid payload" }, { status: 400 });
  }
}
