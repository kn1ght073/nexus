import { NextRequest, NextResponse } from "next/server";

const getBaseUrl = () => {
  return (process.env.NEXUS_API_BASE_URL || "https://nexus-control-plane-uvi8.onrender.com").replace(/\/$/, "");
};

export async function POST(req: NextRequest) {
  try {
    const origin = req.headers.get("origin") || req.nextUrl.origin;
    const redirect_uri = `${origin}/auth/callback`;

    const res = await fetch(`${getBaseUrl()}/api/auth/google/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ redirect_uri }),
    });

    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json({ detail: err }, { status: res.status });
    }

    const data = await res.json();
    const response = NextResponse.json({ url: data.url });

    // Store state & code_verifier in temporary HttpOnly cookies for callback verification
    response.cookies.set("nexus_oauth_state", data.state, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 600,
    });

    if (data.code_verifier) {
      response.cookies.set("nexus_oauth_verifier", data.code_verifier, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        path: "/",
        maxAge: 600,
      });
    }

    return response;
  } catch (err: any) {
    return NextResponse.json({ detail: err.message }, { status: 500 });
  }
}

export async function GET(req: NextRequest) {
  return POST(req);
}
