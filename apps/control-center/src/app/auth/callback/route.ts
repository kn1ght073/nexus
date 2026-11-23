import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const getBaseUrl = () => {
  return (process.env.NEXUS_API_BASE_URL || "https://nexus-control-plane-uvi8.onrender.com").replace(/\/$/, "");
};

export async function GET(req: NextRequest) {
  const searchParams = req.nextUrl.searchParams;
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const error = searchParams.get("error");

  const baseUrl = req.nextUrl.origin;

  if (error || !code || !state) {
    return NextResponse.redirect(`${baseUrl}/login?error=${encodeURIComponent(error || "Missing OAuth code")}`);
  }

  const cookieStore = await cookies();
  const savedState = cookieStore.get("nexus_oauth_state")?.value;
  const codeVerifier = cookieStore.get("nexus_oauth_verifier")?.value;

  if (!savedState || savedState !== state) {
    return NextResponse.redirect(`${baseUrl}/login?error=State%20mismatch`);
  }

  try {
    const res = await fetch(`${getBaseUrl()}/api/auth/google/callback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code,
        state,
        code_verifier: codeVerifier,
      }),
    });

    if (!res.ok) {
      const err = await res.text();
      let detail = err;
      try {
        detail = JSON.parse(err).detail || err;
      } catch {}
      return NextResponse.redirect(`${baseUrl}/login?error=${encodeURIComponent(detail)}`);
    }

    const tokens = await res.json();
    const response = NextResponse.redirect(`${baseUrl}/`);

    // Set secure tokens in HttpOnly cookies
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

    response.cookies.delete("nexus_oauth_state");
    response.cookies.delete("nexus_oauth_verifier");

    return response;
  } catch (err: any) {
    return NextResponse.redirect(`${baseUrl}/login?error=${encodeURIComponent(err.message)}`);
  }
}
