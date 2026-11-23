"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Database,
  HardDrive,
  FolderGit2,
  FileText,
  ListTodo,
  Inbox,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Sparkles,
  Download,
} from "lucide-react";
import { AccountDataSummary } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function ClientDataView() {
  const { data: summary, isLoading } = useQuery<AccountDataSummary>({
    queryKey: ["client-data-summary"],
    queryFn: async () => {
      const res = await fetch("/api/account/data-summary");
      if (!res.ok) throw new Error("Failed to load account data summary");
      return res.json();
    },
  });

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Account Data &amp; Sovereign Storage</h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Inspect personal datasets, edge node synchronize records, and zero-cloud storage metrics.
        </p>
      </div>

      {/* Storage Architecture Callout */}
      <Card className="border-sky-500/20 bg-gradient-to-r from-sky-950/20 to-slate-900/40">
        <CardContent className="p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div className="w-10 h-10 rounded-lg bg-sky-500/10 border border-sky-500/20 grid place-items-center text-sky-400 shrink-0">
              <HardDrive className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">Zero Cloud File Retention Policy</h3>
              <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
                By sovereign design, the NEXUS cloud control plane maintains <strong>zero custodial storage</strong> for
                your documents, voice recordings, or embeddings. Your hardware nodes store all actual files locally.
              </p>
            </div>
          </div>
          <div className="bg-black/40 border border-white/5 rounded-lg px-4 py-2.5 text-center shrink-0">
            <span className="text-[10px] font-mono text-slate-500 block uppercase">Cloud Storage Ingestion</span>
            <span className="text-lg font-bold text-emerald-400 font-mono">0 Bytes</span>
          </div>
        </CardContent>
      </Card>

      {/* Edge Data Counts */}
      <div>
        <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
          <span>Supported Account Entities</span>
          <Badge variant="outline" className="border-white/10 text-slate-400 text-[10px]">LOCAL / SYNC</Badge>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Projects */}
          <Card className="border-white/8 bg-[#0d131f]/70">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-blue-500/10 border border-blue-500/20 grid place-items-center text-blue-400">
                <FolderGit2 className="w-4 h-4" />
              </div>
              <div>
                <p className="text-[11px] font-mono text-slate-400 uppercase">Workspaces &amp; Projects</p>
                <p className="text-xl font-bold text-white mt-0.5">{summary?.stats.projects ?? 0}</p>
              </div>
            </CardContent>
          </Card>

          {/* Notes */}
          <Card className="border-white/8 bg-[#0d131f]/70">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/20 grid place-items-center text-amber-400">
                <FileText className="w-4 h-4" />
              </div>
              <div>
                <p className="text-[11px] font-mono text-slate-400 uppercase">Knowledge Notes</p>
                <p className="text-xl font-bold text-white mt-0.5">{summary?.stats.notes ?? 0}</p>
              </div>
            </CardContent>
          </Card>

          {/* Tasks */}
          <Card className="border-white/8 bg-[#0d131f]/70">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 grid place-items-center text-emerald-400">
                <ListTodo className="w-4 h-4" />
              </div>
              <div>
                <p className="text-[11px] font-mono text-slate-400 uppercase">Tracked Tasks</p>
                <p className="text-xl font-bold text-white mt-0.5">{summary?.stats.tasks ?? 0}</p>
              </div>
            </CardContent>
          </Card>

          {/* Smart Inbox */}
          <Card className="border-white/8 bg-[#0d131f]/70">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-purple-500/10 border border-purple-500/20 grid place-items-center text-purple-400">
                <Inbox className="w-4 h-4" />
              </div>
              <div>
                <p className="text-[11px] font-mono text-slate-400 uppercase">Smart Inbox Items</p>
                <p className="text-xl font-bold text-white mt-0.5">{summary?.stats.inbox_items ?? 0}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Feature Transparency: Implemented vs Non-Implemented/Roadmap */}
      <Card className="border-white/8 bg-[#0d131f]/70">
        <CardHeader className="p-5 border-b border-white/5">
          <CardTitle className="text-base text-white">Feature Transparency Matrix</CardTitle>
          <CardDescription className="text-xs text-slate-400">
            Clear distinction between live production capabilities and sovereign non-custodial boundaries.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Live Operational Features */}
            <div className="space-y-3">
              <h4 className="text-xs font-mono font-bold text-emerald-400 uppercase flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" />
                Active Features (Live)
              </h4>
              <ul className="space-y-2 text-xs text-slate-300">
                <li className="p-2.5 rounded bg-black/30 border border-white/5">
                  <strong className="text-white block">Hardware Device Federation</strong>
                  <span className="text-slate-400 text-[11px]">Register and manage Windows, macOS, Android, and CLI nodes.</span>
                </li>
                <li className="p-2.5 rounded bg-black/30 border border-white/5">
                  <strong className="text-white block">Encrypted Relay Tunnels</strong>
                  <span className="text-slate-400 text-[11px]">ChaCha20-Poly1305 socket bridges for direct peer communication.</span>
                </li>
                <li className="p-2.5 rounded bg-black/30 border border-white/5">
                  <strong className="text-white block">Session Lineage &amp; Invalidation</strong>
                  <span className="text-slate-400 text-[11px]">Token family rotation and instant multi-token family revocation.</span>
                </li>
              </ul>
            </div>

            {/* Sovereign Boundaries & Edge-Only Capabilities */}
            <div className="space-y-3">
              <h4 className="text-xs font-mono font-bold text-sky-400 uppercase flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4" />
                Sovereign Architecture Boundaries
              </h4>
              <ul className="space-y-2 text-xs text-slate-300">
                <li className="p-2.5 rounded bg-black/30 border border-white/5">
                  <strong className="text-white block">Centralized Cloud Vault (Deliberately Disabled)</strong>
                  <span className="text-slate-400 text-[11px]">
                    NEXUS rejects cloud file storage to prevent server-side data leaks and provider lock-in.
                  </span>
                </li>
                <li className="p-2.5 rounded bg-black/30 border border-white/5">
                  <strong className="text-white block">Offline Edge AI (Hardware Dependent)</strong>
                  <span className="text-slate-400 text-[11px]">
                    STT (faster-whisper) and LLM inference (Ollama) execute locally on your physical machine.
                  </span>
                </li>
                <li className="p-2.5 rounded bg-black/30 border border-white/5">
                  <strong className="text-white block">Peer-to-Peer Data Synchronization</strong>
                  <span className="text-slate-400 text-[11px]">
                    Direct device-to-device replication without intermediate cloud ingestion.
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
