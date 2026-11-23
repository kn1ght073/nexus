"use client";

import React, { useState } from "react";
import { Users, Shield, ShieldAlert, CheckCircle2, UserCheck, AlertTriangle } from "lucide-react";
import { User } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

interface OperatorsManagerProps {
  currentUser: User;
  initialUsers: User[];
}

export function OperatorsManager({ currentUser, initialUsers }: OperatorsManagerProps) {
  const [users, setUsers] = useState<User[]>(initialUsers);
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isOwner = currentUser.role === "owner";

  const handleRoleChange = async (userId: number, newRole: "user" | "operator" | "owner") => {
    setErrorMsg(null);
    setLoadingId(userId);

    try {
      const res = await fetch(`/api/operators/${userId}/role`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: newRole }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Failed to update role");
      }

      setUsers(users.map((u) => (u.id === userId ? { ...u, role: newRole } : u)));
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to update user role");
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-white/8">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-sky-400" />
            OPERATOR MANAGEMENT & RBAC
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Role-Based Access Control directory for operators, cluster administrators, and enrolled identities.
          </p>
        </div>
        <Badge
          variant="outline"
          className="font-mono text-xs text-sky-400 border-sky-500/30 uppercase"
        >
          Your Role: {currentUser.role}
        </Badge>
      </div>

      {errorMsg && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* RBAC Rules Description Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        <div className="p-4 rounded-xl bg-[#0c1220]/70 border border-white/8 space-y-1">
          <div className="flex items-center gap-2 text-sky-400 font-semibold">
            <Shield className="w-4 h-4" />
            <span>Owner</span>
          </div>
          <p className="text-slate-400">
            Full root privilege: can manage all devices, nodes, audit records, and assign operator/owner roles.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-[#0c1220]/70 border border-white/8 space-y-1">
          <div className="flex items-center gap-2 text-emerald-400 font-semibold">
            <UserCheck className="w-4 h-4" />
            <span>Operator</span>
          </div>
          <p className="text-slate-400">
            Operational access: can view telemetry, manage fleet endpoints, inspect relay, and view audit trails.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-[#0c1220]/70 border border-white/8 space-y-1">
          <div className="flex items-center gap-2 text-slate-400 font-semibold">
            <Users className="w-4 h-4" />
            <span>User</span>
          </div>
          <p className="text-slate-500">
            Standard endpoint access: sync and personal device coordination only.
          </p>
        </div>
      </div>

      {/* Users Table */}
      <div className="rounded-xl border border-white/8 bg-[#0c1220]/70 overflow-hidden shadow-xl">
        <div className="p-4 border-b border-white/8 flex items-center justify-between">
          <h2 className="text-xs font-semibold tracking-wider text-white">OPERATOR DIRECTORY</h2>
          <span className="text-xs text-slate-400 font-mono">{users.length} enrolled identities</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-black/30 border-b border-white/8 text-slate-400 uppercase tracking-wider font-mono text-[10px]">
              <tr>
                <th className="py-3 px-4">Operator</th>
                <th className="py-3 px-4">UID</th>
                <th className="py-3 px-4">Role</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Enrolled At</th>
                {isOwner && <th className="py-3 px-4 text-right">Assign Role</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              {users.map((u) => {
                const isCurrent = u.id === currentUser.id;
                return (
                  <tr key={u.id} className="hover:bg-white/5 transition-colors">
                    <td className="py-3 px-4 font-medium text-white flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full bg-slate-800 border border-white/10 grid place-items-center text-[10px] font-mono text-sky-400">
                        {u.email.slice(0, 2).toUpperCase()}
                      </div>
                      <span>{u.email}</span>
                      {isCurrent && (
                        <Badge variant="outline" className="text-[9px] px-1 py-0 text-slate-400 border-white/10">
                          YOU
                        </Badge>
                      )}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-400">#{u.id}</td>
                    <td className="py-3 px-4">
                      <Badge
                        variant={u.role === "owner" ? "success" : u.role === "operator" ? "outline" : "secondary"}
                        className="text-[10px] font-mono uppercase"
                      >
                        {u.role}
                      </Badge>
                    </td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center gap-1 font-mono text-[11px] text-emerald-400">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Active
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                      {formatDate(u.created_at)}
                    </td>
                    {isOwner && (
                      <td className="py-3 px-4 text-right">
                        <select
                          disabled={loadingId === u.id}
                          value={u.role}
                          onChange={(e) =>
                            handleRoleChange(u.id, e.target.value as "user" | "operator" | "owner")
                          }
                          className="bg-black/50 border border-white/10 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-sky-400 cursor-pointer"
                        >
                          <option value="user" className="bg-[#0d1322]">
                            user
                          </option>
                          <option value="operator" className="bg-[#0d1322]">
                            operator
                          </option>
                          <option value="owner" className="bg-[#0d1322]">
                            owner
                          </option>
                        </select>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
