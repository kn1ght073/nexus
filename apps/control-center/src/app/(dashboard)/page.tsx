import Link from "next/link";
import {
  Server,
  HardDrive,
  Network,
  Activity,
  ShieldCheck,
  ArrowUpRight,
  Clock,
  Laptop,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { coreApi } from "@/lib/api-server";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function OverviewPage() {
  const [sysRes, devRes, nodeRes, relayRes, actRes] = await Promise.all([
    coreApi.getSystemStatus(),
    coreApi.getDevices(),
    coreApi.getNodes(),
    coreApi.getRelayStatus(),
    coreApi.getActivity(8),
  ]);

  const sys = sysRes.data;
  const devices = devRes.data || [];
  const nodes = nodeRes.data || [];
  const relay = relayRes.data;
  const activity = actRes.data || [];

  const onlineDevices = devices.filter((d) => d.is_online).length;
  const dbConnected = sys?.database.status === "connected";

  return (
    <div className="space-y-6">
      {/* Top Banner / Headline */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-white/8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-xl font-bold tracking-tight text-white">SYSTEM OVERVIEW</h1>
            <Badge variant="outline" className="font-mono text-[10px] text-sky-400 border-sky-500/30">
              CLUSTER ACTIVE
            </Badge>
          </div>
          <p className="text-xs text-slate-400">
            Real-time telemetry, node coordination, and perimeter integrity for NEXUS infrastructure.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/devices"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-500 text-slate-950 text-xs font-semibold hover:bg-sky-400 transition-colors"
          >
            Manage Devices
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
          <Link
            href="/relay"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-slate-300 text-xs font-medium hover:bg-white/10 transition-colors"
          >
            Inspect Relay
          </Link>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* PostgreSQL Database */}
        <Card className="bg-[#0c1220]/70 border-white/8">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-slate-400">Database Engine</CardTitle>
            <HardDrive className="w-4 h-4 text-sky-400" />
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold font-mono text-white">
                {sys?.database.latency_ms !== undefined ? `${sys.database.latency_ms}ms` : "—"}
              </span>
              <Badge
                variant={dbConnected ? "success" : "destructive"}
                className="text-[9px] px-1.5 py-0 uppercase"
              >
                {sys?.database.status || "Unknown"}
              </Badge>
            </div>
            <p className="text-[11px] text-slate-500 mt-1 font-mono truncate">
              {sys?.database.engine || "PostgreSQL Neon"}
            </p>
          </CardContent>
        </Card>

        {/* Registered Devices */}
        <Card className="bg-[#0c1220]/70 border-white/8">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-slate-400">Registered Devices</CardTitle>
            <Laptop className="w-4 h-4 text-indigo-400" />
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold font-mono text-white">{devices.length}</span>
              <span className="text-xs text-emerald-400 font-mono">({onlineDevices} online)</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Cross-platform fleet registered</p>
          </CardContent>
        </Card>

        {/* Coordinated Nodes */}
        <Card className="bg-[#0c1220]/70 border-white/8">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-slate-400">Coordinated Nodes</CardTitle>
            <Server className="w-4 h-4 text-amber-400" />
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold font-mono text-white">{nodes.length}</span>
              <Badge variant="outline" className="text-[9px] font-mono text-amber-400 border-amber-500/30">
                P2P MAIN SERVERS
              </Badge>
            </div>
            <p className="text-[11px] text-slate-500 mt-1 font-mono">
              Heartbeat TTL: {sys?.node_coordination.heartbeat_timeout_sec || 30}s
            </p>
          </CardContent>
        </Card>

        {/* Relay Sockets */}
        <Card className="bg-[#0c1220]/70 border-white/8">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-slate-400">Active Relay Mesh</CardTitle>
            <Network className="w-4 h-4 text-emerald-400" />
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold font-mono text-white">
                {relay?.active_sockets ?? 0}
              </span>
              <span className="text-xs text-slate-400">Sockets</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1 font-mono">
              Nodes listening: {relay?.nodes_listening.length ?? 0}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Grid: Architecture Status & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Coordination & Security Posture */}
        <div className="lg:col-span-1 space-y-4">
          <Card className="bg-[#0c1220]/70 border-white/8">
            <CardHeader className="pb-3">
              <CardTitle className="text-xs font-semibold text-white tracking-wider flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-sky-400" />
                ADMISSION & SECURITY
              </CardTitle>
              <CardDescription className="text-xs text-slate-400">
                Hardened authentication boundaries
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between p-2 rounded-lg bg-black/30 border border-white/5">
                <span className="text-xs text-slate-300">Google OIDC Gate</span>
                <Badge
                  variant={sys?.auth.google_oidc_configured ? "success" : "secondary"}
                  className="text-[9px] font-mono"
                >
                  {sys?.auth.google_oidc_configured ? "ACTIVE" : "UNCONFIGURED"}
                </Badge>
              </div>

              <div className="flex items-center justify-between p-2 rounded-lg bg-black/30 border border-white/5">
                <span className="text-xs text-slate-300">Domain Allowlist</span>
                <Badge
                  variant={sys?.auth.google_allowlist_active ? "success" : "secondary"}
                  className="text-[9px] font-mono"
                >
                  {sys?.auth.google_allowlist_active ? "ENFORCED" : "OPEN"}
                </Badge>
              </div>

              <div className="flex items-center justify-between p-2 rounded-lg bg-black/30 border border-white/5">
                <span className="text-xs text-slate-300">Password Auth</span>
                <Badge
                  variant={sys?.auth.password_auth_allowed ? "outline" : "secondary"}
                  className="text-[9px] font-mono"
                >
                  {sys?.auth.password_auth_allowed ? "ALLOWED" : "RESTRICTED"}
                </Badge>
              </div>

              <div className="flex items-center justify-between p-2 rounded-lg bg-black/30 border border-white/5">
                <span className="text-xs text-slate-300">Relay Mesh Tunnel</span>
                <Badge
                  variant={sys?.node_coordination.relay_enabled ? "success" : "secondary"}
                  className="text-[9px] font-mono"
                >
                  {sys?.node_coordination.relay_enabled ? "ENABLED" : "DISABLED"}
                </Badge>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-[#0c1220]/70 border-white/8">
            <CardHeader className="pb-3">
              <CardTitle className="text-xs font-semibold text-white tracking-wider flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-400" />
                SERVICE TOPOLOGY
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-xs">
              <div className="flex justify-between items-center text-slate-300 py-1 border-b border-white/5">
                <span className="text-slate-400">Control Plane Mode</span>
                <span className="font-mono text-sky-400">{sys?.mode?.toUpperCase() || "CLOUD"}</span>
              </div>
              <div className="flex justify-between items-center text-slate-300 py-1 border-b border-white/5">
                <span className="text-slate-400">Node Pairing TTL</span>
                <span className="font-mono">{sys?.node_coordination.pairing_ttl_sec || 300}s</span>
              </div>
              <div className="flex justify-between items-center text-slate-300 py-1">
                <span className="text-slate-400">Active Operator</span>
                <span className="font-mono text-emerald-400 truncate max-w-[150px]">
                  {sys?.operator.email || "—"}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Activity Stream Table */}
        <div className="lg:col-span-2">
          <Card className="bg-[#0c1220]/70 border-white/8 h-full flex flex-col">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-xs font-semibold text-white tracking-wider flex items-center gap-2">
                  <Clock className="w-4 h-4 text-sky-400" />
                  OPERATIONAL ACTIVITY LOG
                </CardTitle>
                <CardDescription className="text-xs text-slate-400 mt-1">
                  Immutable audit records for control-plane events
                </CardDescription>
              </div>
              <Link href="/audit" className="text-xs text-sky-400 hover:underline">
                View All
              </Link>
            </CardHeader>
            <CardContent className="flex-1 overflow-x-auto">
              {activity.length === 0 ? (
                <div className="text-center py-12 text-xs text-slate-500">
                  No activity events recorded yet.
                </div>
              ) : (
                <div className="divide-y divide-white/5">
                  {activity.map((item) => (
                    <div key={item.id} className="py-2.5 flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-medium text-slate-200">
                            {item.action}
                          </span>
                          {item.device_id && (
                            <Badge variant="outline" className="text-[9px] font-mono px-1 py-0 text-slate-400">
                              DEV #{item.device_id}
                            </Badge>
                          )}
                        </div>
                        {item.detail && (
                          <p className="text-xs text-slate-400 font-mono break-all">{item.detail}</p>
                        )}
                      </div>
                      <span className="text-[11px] font-mono text-slate-500 shrink-0">
                        {formatDate(item.created_at)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
