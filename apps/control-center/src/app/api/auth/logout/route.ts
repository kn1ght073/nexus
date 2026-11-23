import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const getBaseUrl = () => {
  return (process.env.NEXUS_API_BASE_URL || "https://nexus-control-plane-uvi8.onrender.com").replace(/\/$/, "");
};

export async function POST(req: NextRequest) {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("nexus_access_token")?.value;
  const refreshToken = cookieStore.get("nexus_refresh_token")?.value;

  try {
    if (accessToken) {
      await fetch(`${getBaseUrl()}/api/auth/logout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    }
  } catch {}

  const response = NextResponse.json({ ok: true });
  response.cookies.delete("nexus_access_token");
  response.cookies.delete("nexus_refresh_token");
  return response;
}
