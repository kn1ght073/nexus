import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const getBaseUrl = () => {
  return (process.env.NEXUS_API_BASE_URL || "https://nexus-control-plane-uvi8.onrender.com").replace(/\/$/, "");
};

export async function GET(req: NextRequest) {
  const cookieStore = await cookies();
  const token = cookieStore.get("nexus_access_token")?.value;

  if (!token) {
    return NextResponse.json({ authenticated: false, user: null }, { status: 200 });
  }

  try {
    const res = await fetch(`${getBaseUrl()}/api/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    });

    if (!res.ok) {
      return NextResponse.json({ authenticated: false, user: null }, { status: 200 });
    }

    const user = await res.json();
    return NextResponse.json({ authenticated: true, user });
  } catch (err: any) {
    return NextResponse.json({ authenticated: false, error: err.message }, { status: 500 });
  }
}
