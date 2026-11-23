import { Network, Radio, Server, CheckCircle2, ShieldCheck, Terminal, Cpu } from "lucide-react";
import { coreApi } from "@/lib/api-server";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function RelayPage() {
  const { data: relay } = await coreApi.getRelayStatus();

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-white/8">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <Network className="w-5 h-5 text-emerald-400" />
            CONNECTIONS & RELAY MESH
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time WebSocket & TCP multiplexing tunnel connecting distributed edge nodes behind NATs.
          </p>
        </div>
        <Badge
          variant="outline"
          className="font-mono text-xs text-emerald-400 border-emerald-500/30 px-3 py-1 flex items-center gap-1.5"
        >
          <Radio className="w-3.5 h-3.5 animate-pulse" />
          MESH RUNNING
        </Badge>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="bg-[#0c1220]/70 border-white/8">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-slate-400">Active Sockets</CardTitle>
            <Radio className="w-4 h-4 text-emerald-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-white">
              {relay?.active_sockets ?? 0}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Simultaneous WebSocket client streams</p>
          </CardContent>
        </Card>

        <Card className="bg-[#0c1220]/70 border-white/8">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-slate-400">Listening Nodes</CardTitle>
            <Server className="w-4 h-4 text-sky-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-white">
              {relay?.nodes_listening.length ?? 0}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Nodes bound to relay daemon</p>
          </CardContent>
        </Card>

        <Card className="bg-[#0c1220]/70 border-white/8">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-slate-400">Tunnel Encryption</CardTitle>
            <ShieldCheck className="w-4 h-4 text-indigo-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-white">E2E TLS 1.3</div>
            <p className="text-[11px] text-slate-500 mt-1">Zero-knowledge binary stream framing</p>
          </CardContent>
        </Card>
      </div>

      {/* Listening Nodes Table */}
      <div className="rounded-xl border border-white/8 bg-[#0c1220]/70 overflow-hidden shadow-xl">
        <div className="p-4 border-b border-white/8 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-sky-400" />
            <h2 className="text-xs font-semibold tracking-wider text-white">RELAY LISTENERS & SOCKETS</h2>
          </div>
          <span className="text-xs font-mono text-slate-400">
            {relay?.nodes_listening.length ?? 0} active listeners
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-black/30 border-b border-white/8 text-slate-400 uppercase tracking-wider font-mono text-[10px]">
              <tr>
                <th className="py-3 px-4">Node ID</th>
                <th className="py-3 px-4">Device Bound</th>
                <th className="py-3 px-4">Owner ID</th>
                <th className="py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              {!relay?.nodes_listening || relay.nodes_listening.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-slate-500">
                    No active relay sockets connected at this moment.
                  </td>
                </tr>
              ) : (
                relay.nodes_listening.map((n, idx) => (
                  <tr key={idx} className="hover:bg-white/5 transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-white">Node #{n.node_id}</td>
                    <td className="py-3 px-4">
                      <Badge variant="outline" className="font-mono text-[10px]">
                        {n.has_device ? "Device Attached" : "Standalone"}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-400">UID #{n.owner_id}</td>
                    <td className="py-3 px-4">
                      <Badge variant="success" className="font-mono text-[9px]">
                        CONNECTED
                      </Badge>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Attachment Links */}
      <div className="rounded-xl border border-white/8 bg-[#0c1220]/70 overflow-hidden shadow-xl">
        <div className="p-4 border-b border-white/8">
          <h2 className="text-xs font-semibold tracking-wider text-white">ATTACHMENT LINKS HISTORY</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-black/30 border-b border-white/8 text-slate-400 uppercase tracking-wider font-mono text-[10px]">
              <tr>
                <th className="py-3 px-4">Link ID</th>
                <th className="py-3 px-4">Node ID</th>
                <th className="py-3 px-4">Device ID</th>
                <th className="py-3 px-4">Attached At</th>
                <th className="py-3 px-4">Detached At</th>
                <th className="py-3 px-4">State</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              {!relay?.recent_links || relay.recent_links.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No attachment links recorded yet.
                  </td>
                </tr>
              ) : (
                relay.recent_links.map((link) => (
                  <tr key={link.id} className="hover:bg-white/5 transition-colors">
                    <td className="py-3 px-4 font-mono text-white">#{link.id}</td>
                    <td className="py-3 px-4 font-mono text-sky-400">Node #{link.node_id}</td>
                    <td className="py-3 px-4 font-mono text-indigo-400">
                      {link.device_id ? `Dev #${link.device_id}` : "—"}
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                      {link.attached_at ? formatDate(link.attached_at) : "—"}
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                      {link.detached_at ? formatDate(link.detached_at) : "—"}
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant={link.is_active ? "success" : "secondary"} className="font-mono text-[9px]">
                        {link.is_active ? "ACTIVE" : "CLOSED"}
                      </Badge>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* CLI Instruction Box */}
      <div className="p-4 bg-black/40 border border-white/8 rounded-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs">
        <div className="flex items-center gap-3">
          <Terminal className="w-5 h-5 text-emerald-400 shrink-0" />
          <div>
            <p className="font-semibold text-white">Relay Attachment Protocol</p>
            <p className="text-slate-400 text-[11px]">
              Edge nodes establish an outbound WebSocket connection to the Control Plane to receive RPC requests without exposing local ports.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 bg-slate-950 px-3 py-2 rounded-lg border border-white/10 font-mono text-emerald-400 text-xs">
          <span>nexus relay attach --node &lt;NODE_NAME&gt;</span>
        </div>
      </div>
    </div>
  );
}
