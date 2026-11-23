import { Settings, Server, Globe, Key, Database, Shield } from "lucide-react";
import { coreApi } from "@/lib/api-server";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const { data: sys } = await coreApi.getSystemStatus();
  const { data: user } = await coreApi.getCurrentUser();

  const baseUrl = process.env.NEXUS_API_BASE_URL || "https://nexus-control-plane-uvi8.onrender.com";

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-white/8">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <Settings className="w-5 h-5 text-sky-400" />
            CONTROL PLANE CONFIGURATION
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Core API endpoints, perimeter settings, and operator identity bindings.
          </p>
        </div>
        <Badge variant="outline" className="font-mono text-xs text-sky-400 border-sky-500/30">
          CLUSTER CONFIG
        </Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* API & Network Endpoint */}
        <Card className="bg-[#0c1220]/70 border-white/8">
          <CardHeader>
            <CardTitle className="text-xs font-semibold text-white tracking-wider flex items-center gap-2">
              <Globe className="w-4 h-4 text-sky-400" />
              BACKEND API & NETWORKING
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Connection coordinates between Next.js frontend and FastAPI core
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs font-mono">
            <div className="p-3 bg-black/40 rounded-lg border border-white/5 space-y-1">
              <span className="text-[10px] text-slate-500 uppercase block font-semibold">
                NEXUS_API_BASE_URL
              </span>
              <span className="text-sky-400 break-all">{baseUrl}</span>
            </div>

            <div className="flex justify-between items-center py-1.5 border-b border-white/5">
              <span className="text-slate-400">Operating Mode</span>
              <span className="text-slate-200 uppercase">{sys?.mode || "CLOUD"}</span>
            </div>

            <div className="flex justify-between items-center py-1.5 border-b border-white/5">
              <span className="text-slate-400">Service Identifier</span>
              <span className="text-slate-200">{sys?.service || "nexus-core"}</span>
            </div>

            <div className="flex justify-between items-center py-1.5">
              <span className="text-slate-400">Heartbeat Timeout</span>
              <span className="text-slate-200">{sys?.node_coordination.heartbeat_timeout_sec || 30}s</span>
            </div>
          </CardContent>
        </Card>

        {/* Database & Storage */}
        <Card className="bg-[#0c1220]/70 border-white/8">
          <CardHeader>
            <CardTitle className="text-xs font-semibold text-white tracking-wider flex items-center gap-2">
              <Database className="w-4 h-4 text-indigo-400" />
              DATABASE ENGINE & HEALTH
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Primary transactional data store
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs font-mono">
            <div className="p-3 bg-black/40 rounded-lg border border-white/5 space-y-1">
              <span className="text-[10px] text-slate-500 uppercase block font-semibold">
                DATABASE ENGINE
              </span>
              <span className="text-indigo-400">{sys?.database.engine || "PostgreSQL Neon"}</span>
            </div>

            <div className="flex justify-between items-center py-1.5 border-b border-white/5">
              <span className="text-slate-400">Connection Health</span>
              <Badge variant={sys?.database.status === "connected" ? "success" : "destructive"}>
                {sys?.database.status?.toUpperCase() || "UNKNOWN"}
              </Badge>
            </div>

            <div className="flex justify-between items-center py-1.5">
              <span className="text-slate-400">Query Latency</span>
              <span className="text-emerald-400">{sys?.database.latency_ms ?? "—"} ms</span>
            </div>
          </CardContent>
        </Card>

        {/* Authenticated Identity */}
        <Card className="bg-[#0c1220]/70 border-white/8 md:col-span-2">
          <CardHeader>
            <CardTitle className="text-xs font-semibold text-white tracking-wider flex items-center gap-2">
              <Shield className="w-4 h-4 text-emerald-400" />
              OPERATOR IDENTITY & PRIVILEGE
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Identity parameters associated with this active session
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono">
              <div className="p-3 bg-black/40 rounded-lg border border-white/5">
                <span className="text-[10px] text-slate-500 block">AUTHENTICATED EMAIL</span>
                <span className="text-white font-semibold">{user?.email || "—"}</span>
              </div>
              <div className="p-3 bg-black/40 rounded-lg border border-white/5">
                <span className="text-[10px] text-slate-500 block">ASSIGNED ROLE</span>
                <Badge variant="outline" className="text-sky-400 border-sky-500/30 mt-1 uppercase">
                  {user?.role || "user"}
                </Badge>
              </div>
              <div className="p-3 bg-black/40 rounded-lg border border-white/5">
                <span className="text-[10px] text-slate-500 block">USER IDENTIFIER</span>
                <span className="text-slate-300">UID #{user?.id ?? "—"}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
