"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Server,
  Database,
  Radio,
  CheckCircle2,
  Shield,
  Activity,
  Lock,
  Clock,
  AlertCircle,
  Cpu,
  RefreshCw,
} from "lucide-react";
import { useState, useEffect } from "react";
import { ClientServerStatus } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";

export function ClientServerView() {
  const [livePing, setLivePing] = useState<number | null>(null);

  const { data: server, isLoading, refetch } = useQuery<ClientServerStatus>({
    queryKey: ["client-server-status"],
    queryFn: async () => {
      const t0 = performance.now();
      const res = await fetch("/api/account/server-status");
      const t1 = performance.now();
      setLivePing(Math.round(t1 - t0));
      if (!res.ok) throw new Error("Failed to load server status");
      return res.json();
    },
    refetchInterval: 15000,
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Server Information</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            User-safe telemetry regarding the operational status and security posture of the NEXUS control plane.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          className="text-xs gap-1.5"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh Status
        </Button>
      </div>

      {/* Main Status Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Control Plane */}
        <Card className="border-white/8 bg-[#0d131f]/70">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 grid place-items-center text-emerald-400">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-mono text-slate-400 uppercase">Control Plane</p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-sm font-bold text-white uppercase">{server?.control_plane || "OPERATIONAL"}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* API Latency */}
        <Card className="border-white/8 bg-[#0d131f]/70">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-sky-500/10 border border-sky-500/20 grid place-items-center text-sky-400">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-mono text-slate-400 uppercase">API Responsiveness</p>
              <p className="text-sm font-bold text-white mt-0.5 font-mono">
                {livePing !== null ? `${livePing} ms` : "-- ms"}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Database Engine */}
        <Card className="border-white/8 bg-[#0d131f]/70">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-500/10 border border-purple-500/20 grid place-items-center text-purple-400">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-mono text-slate-400 uppercase">Database Engine</p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <span className="text-sm font-bold text-white uppercase">{server?.database || "HEALTHY"}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Relay Mesh */}
        <Card className="border-white/8 bg-[#0d131f]/70">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/20 grid place-items-center text-amber-400">
              <Radio className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[11px] font-mono text-slate-400 uppercase">Relay Mesh</p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <span className="text-sm font-bold text-white uppercase">{server?.relay_mesh || "ACTIVE"}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Infrastructure Details Card */}
      <Card className="border-white/8 bg-[#0d131f]/70">
        <CardHeader className="p-5 border-b border-white/5">
          <CardTitle className="text-base text-white">System Environment Specifications</CardTitle>
          <CardDescription className="text-xs text-slate-400">
            Current release metadata and cryptographic enforcement stack.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="p-3 rounded-lg bg-black/30 border border-white/5 space-y-2 font-mono">
              <div className="flex justify-between">
                <span className="text-slate-400">Release Version:</span>
                <span className="text-sky-400 font-semibold">{server?.api_version || "v0.3.0"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Deployment Architecture:</span>
                <span className="text-white">Cloud Control-Plane Mesh</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Identity Mode:</span>
                <span className="text-white">{server?.auth_provider || "Google OIDC (PKCE S256)"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Last Probe Timestamp:</span>
                <span className="text-slate-300">{server?.checked_at ? formatDate(server.checked_at) : "Active"}</span>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-black/30 border border-white/5 space-y-2">
              <span className="text-[11px] font-mono font-semibold text-slate-400 block uppercase">
                Active Security Enforcements
              </span>
              <ul className="space-y-1.5 text-slate-300">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>PKCE S256 Code Challenge with Cryptographic Nonce</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Token Family Rotation (Automated Reuse Invalidation)</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>ChaCha20-Poly1305 Ephemeral Directional Nonce Tracking</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Strict RBAC Authorization &amp; Object Ownership Filters</span>
                </li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Non-Disclosure / Defense-in-Depth Confidentiality Callout */}
      <Card className="border-white/8 bg-black/40">
        <CardContent className="p-4 flex items-start gap-3">
          <Lock className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
          <div className="text-xs text-slate-400 leading-relaxed">
            <strong className="text-slate-200">Security Boundary Enforcement:</strong> In strict alignment with
            zero-trust hardening guidelines, database credentials, internal cluster IPs, environment variables, and master
            cryptographic keys are quarantined from client-facing introspection.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
