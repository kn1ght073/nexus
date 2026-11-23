import { Activity, Sparkles, Mic, Bot, CheckCircle2, ExternalLink, Terminal, HardDrive } from "lucide-react";
import { coreApi } from "@/lib/api-server";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function ServicesPage() {
  const [pkgRes, statusRes] = await Promise.all([
    coreApi.getPackages(),
    coreApi.getServiceStatus(),
  ]);

  const packages = pkgRes.data?.services || {};
  const env = pkgRes.data?.environment;
  const installed = statusRes.data?.installed || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-white/8">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-sky-400" />
            SERVICES & LOCAL AI ENGINES
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Zero-telemetry local node services for audio transcription, offline LLM inference, and runtime bootstrapping.
          </p>
        </div>
        <Badge variant="outline" className="font-mono text-xs text-sky-400 border-sky-500/30">
          NODE CAPABILITIES
        </Badge>
      </div>

      {/* Services Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Speech-to-Text */}
        <Card className="bg-[#0c1220]/70 border-white/8">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 grid place-items-center text-sky-400">
                  <Mic className="w-4 h-4" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold text-white">
                    Speech-to-Text (STT)
                  </CardTitle>
                  <CardDescription className="text-xs text-slate-400">
                    faster-whisper CT2 engine
                  </CardDescription>
                </div>
              </div>
              <Badge
                variant={installed.stt ? "success" : "secondary"}
                className="text-[10px] font-mono"
              >
                {installed.stt ? "INSTALLED" : "AVAILABLE"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <p className="text-slate-300">
              Offline voice transcription for the Universal Inbox. Runs on CPU/GPU without external API calls or audio leakage.
            </p>
            <div className="p-3 bg-black/40 rounded-lg space-y-1.5 border border-white/5 font-mono text-[11px]">
              <div className="flex justify-between text-slate-400">
                <span>Model Size</span>
                <span className="text-slate-200">~150 MB (base) / ~460 MB (small)</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Distribution</span>
                <span className="text-slate-200">Automated pip install</span>
              </div>
            </div>
            <div className="flex items-center justify-between pt-1">
              <Link
                href="https://github.com/SYSTRAN/faster-whisper"
                target="_blank"
                className="inline-flex items-center gap-1 text-sky-400 hover:underline text-[11px]"
              >
                Documentation <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* Local LLM */}
        <Card className="bg-[#0c1220]/70 border-white/8">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 grid place-items-center text-indigo-400">
                  <Bot className="w-4 h-4" />
                </div>
                <div>
                  <CardTitle className="text-sm font-semibold text-white">
                    Local LLM Intent Extraction
                  </CardTitle>
                  <CardDescription className="text-xs text-slate-400">
                    Ollama Native Bridge
                  </CardDescription>
                </div>
              </div>
              <Badge
                variant={installed.llm ? "success" : "secondary"}
                className="text-[10px] font-mono"
              >
                {installed.llm ? "DETECTED" : "UNREACHABLE"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <p className="text-slate-300">
              Local intent extraction from quick voice and text notes. Probed passively via local HTTP endpoint at 127.0.0.1:11434.
            </p>
            <div className="p-3 bg-black/40 rounded-lg space-y-1.5 border border-white/5 font-mono text-[11px]">
              <div className="flex justify-between text-slate-400">
                <span>Target Model</span>
                <span className="text-slate-200">llama3.2 3B (~2 GB)</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Probe Endpoint</span>
                <span className="text-slate-200">http://127.0.0.1:11434</span>
              </div>
            </div>
            <div className="flex items-center justify-between pt-1">
              <Link
                href="https://ollama.com"
                target="_blank"
                className="inline-flex items-center gap-1 text-indigo-400 hover:underline text-[11px]"
              >
                Download Ollama <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Environment & Bootstrap Details */}
      {env && (
        <Card className="bg-[#0c1220]/70 border-white/8">
          <CardHeader>
            <CardTitle className="text-xs font-semibold text-white tracking-wider flex items-center gap-2">
              <HardDrive className="w-4 h-4 text-emerald-400" />
              ENVIRONMENT RUNTIME & BOOTSTRAP PLAN
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Machine-readable setup specification published by the control plane
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-xs font-mono">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="p-3 bg-black/30 rounded-lg border border-white/5">
                <span className="text-slate-500 block text-[10px]">PACKAGE MANAGER ACCELERATOR</span>
                <span className="text-emerald-400 font-semibold text-xs">
                  {env.uv_available ? "Astral uv Available (Fast)" : "Standard pip (Fallback)"}
                </span>
              </div>
              <div className="p-3 bg-black/30 rounded-lg border border-white/5">
                <span className="text-slate-500 block text-[10px]">INDEX URL</span>
                <span className="text-slate-200 truncate block text-xs">{env.index_url}</span>
              </div>
            </div>

            <div>
              <span className="text-slate-400 text-xs block mb-1.5 font-sans font-semibold">
                Execution Commands
              </span>
              <div className="p-3 bg-black/50 rounded-lg border border-white/5 space-y-1">
                {env.commands.map((cmd, idx) => (
                  <div key={idx} className="text-slate-300 text-[11px]">
                    <span className="text-slate-600 select-none">$ </span>
                    {cmd}
                  </div>
                ))}
              </div>
            </div>

            <div>
              <span className="text-slate-400 text-xs block mb-1.5 font-sans font-semibold">
                Target Requirements
              </span>
              <div className="flex flex-wrap gap-1.5">
                {env.requirements.map((req, idx) => (
                  <Badge key={idx} variant="secondary" className="text-[10px] bg-white/5 text-slate-300">
                    {req}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
