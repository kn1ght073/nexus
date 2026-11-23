import Link from "next/link";
import { Activity, Github } from "lucide-react";
import { coreApi } from "@/lib/api-server";

export async function Header() {
  const { data: health } = await coreApi.getHealth();
  const isHealthy = health?.status === "ok";

  return (
    <header className="h-14 border-b border-white/8 bg-[#080b11]/80 backdrop-blur-md sticky top-0 z-30 px-6 flex items-center justify-between">
      <div className="flex items-center gap-3 text-xs">
        <span className="text-slate-500 font-mono">NEXUS</span>
        <span className="text-slate-600">/</span>
        <span className="text-slate-300 font-semibold tracking-wide">CONTROL CENTER</span>
      </div>

      <div className="flex items-center gap-4">
        {/* Real-time Telemetry Pill */}
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-black/40 border border-white/8 text-xs font-mono">
          <span
            className={`w-2 h-2 rounded-full ${
              isHealthy ? "bg-emerald-400 shadow-[0_0_8px_#34d399]" : "bg-rose-400 shadow-[0_0_8px_#f43f5e]"
            }`}
          />
          <span className="text-slate-400">{health?.service?.toUpperCase() || "CORE-API"}</span>
          <span className="text-sky-400 font-semibold">[{health?.mode?.toUpperCase() || "LIVE"}]</span>
        </div>

        <Link
          href="https://github.com/kn1ght073/nexus"
          target="_blank"
          rel="noopener noreferrer"
          className="text-slate-400 hover:text-white transition-colors"
          title="GitHub Repository"
        >
          <Github className="w-4 h-4" />
        </Link>
      </div>
    </header>
  );
}
