"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Hexagon, Key, ArrowRight, ShieldCheck, AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

export default function LoginPage() {
  const router = useRouter();
  const [sessionToken, setSessionToken] = useState("");
  const [showTokenInput, setShowTokenInput] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGoogleSignIn = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch("/api/auth/google/start", { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Google OIDC service unavailable");
      if (data.url) {
        if (data.url.includes("client_id=nexus-google-client-id")) {
          throw new Error(
            "Google OAuth is not configured on Render: NEXUS_GOOGLE_CLIENT_ID is missing from environment. Add NEXUS_GOOGLE_CLIENT_ID in the Render dashboard."
          );
        }
        window.location.href = data.url;
      }
    } catch (err: any) {
      setError(err.message || "Failed to initiate Google sign-in");
    } finally {
      setLoading(false);
    }
  };

  const handleTokenSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionToken.trim()) return;
    setError(null);
    setLoading(true);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: sessionToken.trim() }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Session authentication failed");
      }

      router.push("/");
      router.refresh();
    } catch (err: any) {
      setError(err.message || "Invalid session token");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#080b11] p-4 relative overflow-hidden">
      {/* Background radial glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-sky-500/5 blur-[120px] rounded-full pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        {/* Top Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-sky-500/10 border border-sky-500/20 text-sky-400 mb-4 shadow-[0_0_20px_rgba(56,189,248,0.15)]">
            <Hexagon className="w-6 h-6" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-white">NEXUS CONTROL CENTER</h1>
          <p className="text-xs text-slate-400 mt-1">Authorized Operator Access & Infrastructure Console</p>
        </div>

        {/* Form Container */}
        <div className="rounded-xl border border-white/10 bg-[#0d1322]/90 backdrop-blur-md p-6 shadow-2xl">
          <div className="mb-6 text-center">
            <span className="inline-block px-2.5 py-1 rounded-full text-[10px] font-mono uppercase bg-sky-500/10 text-sky-400 border border-sky-500/20">
              Admission Policy: Google OAuth Only
            </span>
            <p className="text-xs text-slate-400 mt-2">
              All operator identity registration and session authorizations are exclusively managed via Google OAuth.
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Google OIDC Button */}
          <Button
            type="button"
            variant="outline"
            disabled={loading}
            className="w-full mb-4 flex items-center justify-center gap-2 border-white/15 bg-white/5 hover:bg-white/10 text-white text-xs h-11 font-medium transition-all"
            onClick={handleGoogleSignIn}
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Connecting to Google...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                Continue with Google OAuth
              </>
            )}
          </Button>

          {/* Token Fallback Toggle */}
          <div className="relative my-4">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-white/8" />
            </div>
            <div className="relative flex justify-center text-[10px] uppercase font-mono">
              <button
                type="button"
                onClick={() => setShowTokenInput(!showTokenInput)}
                className="bg-[#0d1322] px-2 text-slate-500 hover:text-slate-300 transition-colors"
              >
                {showTokenInput ? "Hide session token input" : "Or enter session token"}
              </button>
            </div>
          </div>

          {/* Session Token Form */}
          {showTokenInput && (
            <form onSubmit={handleTokenSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">NEXUS Session Token</label>
                <div className="relative">
                  <Key className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                  <Input
                    type="password"
                    required
                    placeholder="eyJhbGciOiJIUzI1NiIsIn..."
                    value={sessionToken}
                    onChange={(e) => setSessionToken(e.target.value)}
                    className="pl-9 h-10 font-mono text-xs"
                  />
                </div>
              </div>

              <Button type="submit" disabled={loading} className="w-full h-10 text-xs font-semibold">
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    Verifying Token...
                  </>
                ) : (
                  <>
                    Authenticate with Token
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </>
                )}
              </Button>
            </form>
          )}

          {/* Security Status Footnote */}
          <div className="mt-6 pt-4 border-t border-white/8 flex items-center justify-between text-[11px] text-slate-400">
            <div className="flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>TLS 1.3 & PKCE Guarded</span>
            </div>
            <Badge variant="outline" className="text-[9px] font-mono border-white/10 text-slate-400">
              GOOGLE-OIDC-ONLY
            </Badge>
          </div>
        </div>
      </div>
    </div>
  );
}
