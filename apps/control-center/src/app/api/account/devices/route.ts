import { NextResponse } from "next/server";
import { coreApi } from "@/lib/api-server";

export async function GET() {
  const { data, error, status } = await coreApi.getAccountDevices();
  if (error) {
    return NextResponse.json({ error }, { status });
  }
  return NextResponse.json(data);
}
