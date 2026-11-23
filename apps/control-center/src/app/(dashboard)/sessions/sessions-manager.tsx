"use client";

import React, { useState } from "react";
import { KeyRound, ShieldAlert, CheckCircle2, XCircle, Trash2, Globe, Clock, Laptop } from "lucide-react";
import { SessionRecord } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

interface SessionsManagerProps {
  initialSessions: SessionRecord[];
}

export function SessionsManager({ initialSessions }: SessionsManagerProps) {
  const [sessions, setSessions] = useState<SessionRecord[]>(initialSessions);
  const [revokingId, setRevokingId] = useState<number | null>(null);

  const handleRevoke = async (id: number) => {
    setRevokingId(id);
    try {
      const res = await fetch(`/api/auth/sessions/${id}`, { method: "DELETE" });
      if (res.ok) {
        setSessions(
          sessions.map((s) =>
            s.id === id ? { ...s, revoked_at: new Date().toISOString() } : s
          )
        );
      }
    } catch (err) {
      console.error("Revoke error:", err);
    } finally {
      setRevokingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-white/8">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <KeyRound className="w-5 h-5 text-sky-400" />
            SESSIONS & IDENTITY ROTATION
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Server-side refresh token lineages, active web and device sessions, and instant family-wide revocation.
          </p>
        </div>
        <Badge variant="outline" className="font-mono text-xs text-sky-400 border-sky-500/30">
          LINEAGE TRACKING ACTIVE
        </Badge>
      </div>

      {/* Info Banner */}
      <div className="p-4 bg-sky-500/5 border border-sky-500/20 rounded-xl flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-sky-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-300 space-y-1">
          <p className="font-semibold text-white">Cryptographic Token Family Rotation</p>
          <p className="text-slate-400">
            Every token refresh generates a fresh pair while retiring the old token. If an attacker attempts to replay a previously rotated refresh token, the control plane immediately revokes the entire session lineage.
          </p>
        </div>
      </div>

      {/* Sessions Table */}
      <div className="rounded-xl border border-white/8 bg-[#0c1220]/70 overflow-hidden shadow-xl">
        <div className="p-4 border-b border-white/8 flex items-center justify-between">
          <h2 className="text-xs font-semibold tracking-wider text-white">SESSION REGISTRY</h2>
          <span className="text-xs text-slate-400 font-mono">{sessions.length} sessions listed</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-black/30 border-b border-white/8 text-slate-400 uppercase tracking-wider font-mono text-[10px]">
              <tr>
                <th className="py-3 px-4">Session ID</th>
                <th className="py-3 px-4">Origin / Client</th>
                <th className="py-3 px-4">Last IP</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Issued / Expires</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              {sessions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No active sessions found.
                  </td>
                </tr>
              ) : (
                sessions.map((sess) => {
                  const isRevoked = !!sess.revoked_at;
                  const isRotated = !!sess.rotated_at;
                  const isExpired = new Date(sess.expires_at) < new Date();
                  const isActive = !isRevoked && !isRotated && !isExpired;

                  return (
                    <tr key={sess.id} className="hover:bg-white/5 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-white">
                        SESS #{sess.id}
                      </td>
                      <td className="py-3 px-4 font-mono">
                        <div className="flex items-center gap-1.5 text-slate-200">
                          {sess.device_id ? (
                            <>
                              <Laptop className="w-3.5 h-3.5 text-indigo-400" />
                              <span>Dev #{sess.device_id}</span>
                            </>
                          ) : (
                            <>
                              <Globe className="w-3.5 h-3.5 text-sky-400" />
                              <span>{sess.created_via}</span>
                            </>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-400">
                        {sess.last_used_ip || "127.0.0.1"}
                      </td>
                      <td className="py-3 px-4">
                        {isRevoked ? (
                          <Badge variant="destructive" className="font-mono text-[9px]">
                            REVOKED
                          </Badge>
                        ) : isRotated ? (
                          <Badge variant="secondary" className="font-mono text-[9px] text-slate-400">
                            ROTATED
                          </Badge>
                        ) : isExpired ? (
                          <Badge variant="outline" className="font-mono text-[9px] text-slate-500">
                            EXPIRED
                          </Badge>
                        ) : (
                          <Badge variant="success" className="font-mono text-[9px]">
                            ACTIVE
                          </Badge>
                        )}
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                        <div>Issued: {formatDate(sess.issued_at)}</div>
                        <div className="text-slate-500 text-[10px]">Exp: {formatDate(sess.expires_at)}</div>
                      </td>
                      <td className="py-3 px-4 text-right">
                        {isActive && (
                          <Button
                            variant="destructive"
                            size="sm"
                            disabled={revokingId === sess.id}
                            onClick={() => handleRevoke(sess.id)}
                            className="h-7 text-[11px] px-2.5"
                          >
                            <Trash2 className="w-3 h-3 mr-1" />
                            {revokingId === sess.id ? "Revoking..." : "Revoke"}
                          </Button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
