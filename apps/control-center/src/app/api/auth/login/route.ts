import { NextRequest, NextResponse } from "next/server";

const getBaseUrl = () => {
  return (process.env.NEXUS_API_BASE_URL || "https://nexus-control-plane-uvi8.onrender.com").replace(/\/$/, "");
};

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { email, password, mode } = body;

    const endpoint = mode === "register" ? "/api/auth/register" : "/api/auth/login";
    const res = await fetch(`${getBaseUrl()}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const text = await res.text();
      let detail = text;
      try {
        const j = JSON.parse(text);
        detail = j.detail || text;
      } catch {}
      return NextResponse.json({ detail }, { status: res.status });
    }

    if (mode === "register") {
      // Automatic login after register
      const loginRes = await fetch(`${getBaseUrl()}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!loginRes.ok) {
        return NextResponse.json({ detail: "Registered successfully. Please log in." }, { status: 200 });
      }
      const tokens = await loginRes.json();
      const response = NextResponse.json({ ok: true, user: tokens });
      
      response.cookies.set("nexus_access_token", tokens.access_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        path: "/",
        maxAge: 30 * 60, // 30 mins
      });
      if (tokens.refresh_token) {
        response.cookies.set("nexus_refresh_token", tokens.refresh_token, {
          httpOnly: true,
          secure: process.env.NODE_ENV === "production",
          sameSite: "lax",
          path: "/",
          maxAge: 30 * 24 * 60 * 60, // 30 days
        });
      }
      return response;
    }

    const tokens = await res.json();
    const response = NextResponse.json({ ok: true });
    
    // Set secure HttpOnly cookies
    response.cookies.set("nexus_access_token", tokens.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 30 * 60,
    });

    if (tokens.refresh_token) {
      response.cookies.set("nexus_refresh_token", tokens.refresh_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        path: "/",
        maxAge: 30 * 24 * 60 * 60,
      });
    }

    return response;
  } catch (err: any) {
    return NextResponse.json({ detail: err.message || "Authentication service failed" }, { status: 500 });
  }
}
