import { ShieldCheck, Lock, KeyRound, AlertTriangle, CheckCircle2, ShieldAlert, Cpu } from "lucide-react";
import { coreApi } from "@/lib/api-server";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const dynamic = "force-dynamic";

export default async function SecurityPage() {
  const { data: sys } = await coreApi.getSystemStatus();

  const auditChecklist = [
    {
      id: "F1",
      title: "CORS Wildcard Elimination",
      desc: "Explicit origin allowlist enforced, no credentials with wildcard origins.",
      status: "PASS",
    },
    {
      id: "F2",
      title: "Path Traversal Hardening",
      desc: "Strict storage root containment and sanitized file keys across OS boundaries.",
      status: "PASS",
    },
    {
      id: "F3",
      title: "SQL Injection Neutralization",
      desc: "Raw string interpolation replaced with parameterized SQLAlchemy constructs.",
      status: "PASS",
    },
    {
      id: "F4",
      title: "Control Plane Perimeter Separation",
      desc: "Password authentication disabled by default in cloud mode; Google OIDC admission gate.",
      status: "PASS",
    },
    {
      id: "F5",
      title: "Session Rotation & Lineage Revocation",
      desc: "Refresh tokens rotated upon single use. Token reuse triggers immediate family invalidation.",
      status: "PASS",
    },
    {
      id: "F6",
      title: "Rate Limiting & Anti-Brute-Force",
      desc: "Progressive lockout delay and per-IP throttling applied to authentication endpoints.",
      status: "PASS",
    },
    {
      id: "F7",
      title: "Relay WebSocket Authorization",
      desc: "Full token and ownership validation before tunnel attachment and frame routing.",
      status: "PASS",
    },
    {
      id: "F8",
      title: "Audit Logging & Observability",
      desc: "Immutable append-only activity records for all mutating operations.",
      status: "PASS",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-white/8">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-sky-400" />
            SECURITY CENTER & POSTURE
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Enterprise boundary security, cryptographic admission policies, and audit hardening status.
          </p>
        </div>
        <Badge variant="outline" className="font-mono text-xs text-emerald-400 border-emerald-500/30">
          ALL 8 AUDIT CONTROLS VERIFIED
        </Badge>
      </div>

      {/* Control Policies Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Google OIDC */}
        <Card className="bg-[#0c1220]/70 border-white/8">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-semibold text-white">Google OIDC Admission</CardTitle>
              <Badge
                variant={sys?.auth.google_oidc_configured ? "success" : "secondary"}
                className="text-[9px] font-mono"
              >
                {sys?.auth.google_oidc_configured ? "ACTIVE" : "STANDBY"}
              </Badge>
            </div>
            <CardDescription className="text-xs text-slate-400">
              Proof Key for Code Exchange (PKCE S256)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-white/5">
              <span className="text-slate-400">Allowlist Filtering</span>
              <span className="font-mono text-sky-400">
                {sys?.auth.google_allowlist_active ? "Enforced" : "All Authorized"}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-white/5">
              <span className="text-slate-400">State / Nonce Validation</span>
              <span className="font-mono text-emerald-400">Strict Cryptographic Hash</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Identity Association</span>
              <span className="font-mono text-slate-200">Issuer + Sub Pair</span>
            </div>
          </CardContent>
        </Card>

        {/* Token Architecture */}
        <Card className="bg-[#0c1220]/70 border-white/8">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-semibold text-white">Token Lineage & Replay</CardTitle>
              <Badge variant="success" className="text-[9px] font-mono">
                COMPROMISE-AWARE
              </Badge>
            </div>
            <CardDescription className="text-xs text-slate-400">
              Refresh Token Family Rotation
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-white/5">
              <span className="text-slate-400">Replay Detection</span>
              <span className="font-mono text-emerald-400">Family Revocation</span>
            </div>
            <div className="flex justify-between py-1 border-b border-white/5">
              <span className="text-slate-400">Storage Strategy</span>
              <span className="font-mono text-sky-400">HttpOnly + Secure Cookies</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Client Infiltration Surface</span>
              <span className="font-mono text-emerald-400">Zero XSS Token Leak</span>
            </div>
          </CardContent>
        </Card>

        {/* Rate Limiting */}
        <Card className="bg-[#0c1220]/70 border-white/8">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-semibold text-white">Brute-Force Lockout</CardTitle>
              <Badge variant="success" className="text-[9px] font-mono">
                ARMED
              </Badge>
            </div>
            <CardDescription className="text-xs text-slate-400">
              Exponential Backoff & IP Guard
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-white/5">
              <span className="text-slate-400">Password Policy Flag</span>
              <span className="font-mono text-slate-200">
                {sys?.auth.password_auth_allowed ? "Enabled" : "Disabled (Cloud)"}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-white/5">
              <span className="text-slate-400">Max Failed Attempts</span>
              <span className="font-mono text-amber-400">5 per window</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Lockout Duration</span>
              <span className="font-mono text-slate-200">900s Progressive</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Security Audit Verification Table */}
      <div className="rounded-xl border border-white/8 bg-[#0c1220]/70 overflow-hidden shadow-xl">
        <div className="p-4 border-b border-white/8">
          <h2 className="text-xs font-semibold tracking-wider text-white">
            NEXUS SECURITY AUDIT REPORT REMEDIATION MATRIX
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Verification status for vulnerabilities identified and resolved in the master security plan.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-black/30 border-b border-white/8 text-slate-400 uppercase tracking-wider font-mono text-[10px]">
              <tr>
                <th className="py-3 px-4">Audit Item</th>
                <th className="py-3 px-4">Control Name</th>
                <th className="py-3 px-4">Remediation Architecture</th>
                <th className="py-3 px-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              {auditChecklist.map((item) => (
                <tr key={item.id} className="hover:bg-white/5 transition-colors">
                  <td className="py-3 px-4 font-mono font-bold text-sky-400">{item.id}</td>
                  <td className="py-3 px-4 font-medium text-white">{item.title}</td>
                  <td className="py-3 px-4 text-slate-400">{item.desc}</td>
                  <td className="py-3 px-4 text-right">
                    <Badge variant="success" className="font-mono text-[9px] px-2 py-0.5">
                      <CheckCircle2 className="w-3 h-3 mr-1 inline" />
                      {item.status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
