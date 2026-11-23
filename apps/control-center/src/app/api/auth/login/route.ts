import { NextRequest, NextResponse } from "next/server";

const getBaseUrl = () => {
  return (process.env.NEXUS_API_BASE_URL || "https://nexus-control-plane-uvi8.onrender.com").replace(/\/$/, "");
};

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { token, email, password } = body;

    // Direct token validation flow
    if (token) {
      const meRes = await fetch(`${getBaseUrl()}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!meRes.ok) {
        return NextResponse.json({ detail: "Invalid or expired session token" }, { status: 401 });
      }
      const user = await meRes.json();
      const response = NextResponse.json({ ok: true, user });

      response.cookies.set("nexus_access_token", token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        path: "/",
        maxAge: 30 * 24 * 60 * 60,
      });

      return response;
    }

    // Password authentication and registration are strictly prohibited
    return NextResponse.json(
      {
        detail:
          "Password authentication and registration are disabled. Please authenticate exclusively using Google OAuth.",
      },
      { status: 403 }
    );
  } catch (err: any) {
    return NextResponse.json({ detail: err.message || "Authentication service failed" }, { status: 500 });
  }
}
