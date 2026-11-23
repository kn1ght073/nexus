"use client";

import { useQuery } from "@tanstack/react-query";
import {
  User,
  Shield,
  Laptop,
  KeyRound,
  CheckCircle2,
  Calendar,
  Copy,
  Check,
  AlertCircle,
  ExternalLink,
} from "lucide-react";
import { useState } from "react";
import { AccountOverview } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";

export function AccountOverviewView() {
  const [copied, setCopied] = useState(false);

  const { data: overview, isLoading, error } = useQuery<AccountOverview>({
    queryKey: ["account-overview"],
    queryFn: async () => {
      const res = await fetch("/api/account/overview");
      if (!res.ok) throw new Error("Failed to load account overview");
      return res.json();
    },
  });

  const copyId = (id: number) => {
    navigator.clipboard.writeText(`NX-${String(id).padStart(6, "0")}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-40 rounded-xl bg-white/5 border border-white/5" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="h-28 rounded-xl bg-white/5 border border-white/5" />
          <div className="h-28 rounded-xl bg-white/5 border border-white/5" />
          <div className="h-28 rounded-xl bg-white/5 border border-white/5" />
        </div>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="p-8 text-center rounded-xl bg-rose-500/5 border border-rose-500/20 text-rose-400">
        <AlertCircle className="w-8 h-8 mx-auto mb-2 text-rose-400" />
        <p className="font-semibold text-sm">Unable to retrieve account overview</p>
        <p className="text-xs text-slate-400 mt-1">Please verify network connectivity to the control plane.</p>
      </div>
    );
  }

  const google = overview.google_identity;
  const formattedId = `NX-${String(overview.id).padStart(6, "0")}`;

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Account Overview</h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Manage your verified sovereign identity, Google account linkage, and hardware nodes.
        </p>
      </div>

      {/* Hero Profile Card */}
      <Card className="border-white/10 bg-gradient-to-r from-sky-950/20 via-slate-900/40 to-slate-900/60 shadow-xl overflow-hidden relative">
        <div className="absolute top-0 right-0 w-80 h-full bg-radial from-sky-500/10 to-transparent pointer-events-none" />
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
            <div className="flex items-center gap-4">
              {google?.picture_url ? (
                <img
                  src={google.picture_url}
                  alt={overview.display_name || overview.email}
                  className="w-16 h-16 rounded-full border-2 border-sky-400/30 object-cover shadow-lg"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <div className="w-16 h-16 rounded-full bg-sky-500/20 border-2 border-sky-400/30 text-sky-300 font-bold text-xl grid place-items-center uppercase shadow-lg">
                  {overview.email.slice(0, 2)}
                </div>
              )}

              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-bold text-white">
                    {google?.name || overview.display_name || overview.email.split("@")[0]}
                  </h3>
                  <Badge variant="outline" className="border-emerald-500/30 text-emerald-400 text-[10px] bg-emerald-500/10">
                    <CheckCircle2 className="w-3 h-3 mr-1 inline" />
                    VERIFIED
                  </Badge>
                  {overview.role !== "user" && (
                    <Badge variant="outline" className="border-amber-500/30 text-amber-400 text-[10px] bg-amber-500/10 uppercase">
                      {overview.role}
                    </Badge>
                  )}
                </div>

                <p className="text-xs text-slate-400 mt-0.5 font-mono">{overview.email}</p>

                <div className="flex flex-wrap items-center gap-4 mt-3 text-xs text-slate-400">
                  <div className="flex items-center gap-1.5 font-mono text-[11px] bg-white/5 px-2.5 py-1 rounded border border-white/5">
                    <span className="text-slate-500">ID:</span>
                    <span className="text-sky-400 font-semibold">{formattedId}</span>
                    <button
                      onClick={() => copyId(overview.id)}
                      className="ml-1 text-slate-400 hover:text-white transition-colors"
                      title="Copy Nexus Account ID"
                    >
                      {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>

                  <div className="flex items-center gap-1.5 text-[11px]">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    <span>Member since {formatDate(overview.created_at)}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Account Status Badge */}
            <div className="bg-black/30 border border-white/5 rounded-lg p-3 text-right">
              <span className="text-[10px] font-mono text-slate-500 block uppercase">Identity Provider</span>
              <span className="text-xs font-semibold text-white flex items-center justify-end gap-1.5 mt-0.5">
                {google?.linked ? (
                  <>
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                    Google OIDC
                  </>
                ) : (
                  <>
                    <span className="w-2 h-2 rounded-full bg-amber-400" />
                    Local Master Passphrase
                  </>
                )}
              </span>
              <span className="text-[10px] text-slate-400 block mt-1">
                {google?.linked_at ? `Linked ${formatDate(google.linked_at)}` : "Sovereign Account"}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Linked Devices */}
        <Card className="border-white/8 bg-[#0d131f]/70">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-sky-500/10 border border-sky-500/20 grid place-items-center text-sky-400">
              <Laptop className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-mono text-slate-400 uppercase">Linked Devices</p>
              <div className="flex items-baseline gap-2 mt-0.5">
                <span className="text-2xl font-bold text-white">{overview.device_stats.total}</span>
                <span className="text-xs text-emerald-400 font-medium">
                  {overview.device_stats.active} online
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Active Sessions */}
        <Card className="border-white/8 bg-[#0d131f]/70">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 grid place-items-center text-emerald-400">
              <KeyRound className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-mono text-slate-400 uppercase">Active Sessions</p>
              <div className="flex items-baseline gap-2 mt-0.5">
                <span className="text-2xl font-bold text-white">{overview.session_stats.active}</span>
                <span className="text-xs text-slate-400">
                  of {overview.session_stats.total} total
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Security Integrity */}
        <Card className="border-white/8 bg-[#0d131f]/70">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-purple-500/10 border border-purple-500/20 grid place-items-center text-purple-400">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-mono text-slate-400 uppercase">Token Family Defense</p>
              <p className="text-sm font-semibold text-white mt-1">PKCE &amp; Rotation Guard</p>
              <p className="text-[10px] text-slate-400">Strict reuse invalidation</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Architecture Notice Banner */}
      <Card className="border-white/8 bg-black/40">
        <CardContent className="p-4 flex items-start gap-3">
          <Shield className="w-4 h-4 text-sky-400 mt-0.5 shrink-0" />
          <div className="text-xs text-slate-400 leading-relaxed">
            <strong className="text-slate-200">Sovereign Architecture Guarantee:</strong> Your account is protected by
            mutual authentication. The NEXUS cloud control plane coordinates identity verification and encrypted relay
            routing without storing personal notes, voice transcripts, or documents in the cloud.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
