import { NextRequest, NextResponse } from "next/server";
import { coreApi } from "@/lib/api-server";

export async function GET() {
  const { data, error, status } = await coreApi.getDevices();
  if (error) {
    return NextResponse.json({ error }, { status });
  }
  return NextResponse.json(data);
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { data, error, status } = await coreApi.registerDevice(body);
    if (error) {
      return NextResponse.json({ error }, { status });
    }
    return NextResponse.json(data, { status: 201 });
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Invalid payload" }, { status: 400 });
  }
}
