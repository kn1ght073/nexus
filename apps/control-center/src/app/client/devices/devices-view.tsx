"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  Laptop,
  Smartphone,
  Terminal,
  Monitor,
  KeyRound,
  Trash2,
  AlertTriangle,
  Info,
  Clock,
  ShieldAlert,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { DeviceRecord, SessionRecord } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { formatDate } from "@/lib/utils";

export function ClientDevicesView() {
  const queryClient = useQueryClient();
  const [deviceToRevoke, setDeviceToRevoke] = useState<DeviceRecord | null>(null);
  const [sessionToRevoke, setSessionToRevoke] = useState<SessionRecord | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // 1. Devices query
  const { data: devices = [], isLoading: loadingDevices } = useQuery<DeviceRecord[]>({
    queryKey: ["client-devices"],
    queryFn: async () => {
      const res = await fetch("/api/account/devices");
      if (!res.ok) throw new Error("Failed to load devices");
      return res.json();
    },
  });

  // 2. Sessions query
  const { data: sessions = [], isLoading: loadingSessions } = useQuery<SessionRecord[]>({
    queryKey: ["client-sessions"],
    queryFn: async () => {
      const res = await fetch("/api/account/sessions");
      if (!res.ok) throw new Error("Failed to load sessions");
      return res.json();
    },
  });

  // Device Revocation Mutation
  const revokeDeviceMutation = useMutation({
    mutationFn: async (deviceId: number) => {
      const res = await fetch(`/api/account/devices/${deviceId}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || "Failed to revoke device");
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["client-devices"] });
      queryClient.invalidateQueries({ queryKey: ["account-overview"] });
      setDeviceToRevoke(null);
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.message);
    },
  });

  // Session Revocation Mutation
  const revokeSessionMutation = useMutation({
    mutationFn: async (sessionId: number) => {
      const res = await fetch(`/api/account/sessions/${sessionId}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || "Failed to revoke session");
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["client-sessions"] });
      queryClient.invalidateQueries({ queryKey: ["account-overview"] });
      setSessionToRevoke(null);
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.message);
    },
  });

  const getPlatformIcon = (platform: string) => {
    switch (platform.toLowerCase()) {
      case "windows":
      case "macos":
      case "linux":
        return <Monitor className="w-4 h-4 text-sky-400" />;
      case "android":
      case "ios":
        return <Smartphone className="w-4 h-4 text-emerald-400" />;
      case "cli":
        return <Terminal className="w-4 h-4 text-amber-400" />;
      default:
        return <Laptop className="w-4 h-4 text-slate-400" />;
    }
  };

  const parseUserAgent = (ua?: string | null) => {
    if (!ua) return "Nexus Sovereign Client";
    if (ua.includes("Chrome")) return "Google Chrome";
    if (ua.includes("Safari") && !ua.includes("Chrome")) return "Apple Safari";
    if (ua.includes("Firefox")) return "Mozilla Firefox";
    if (ua.includes("Edge")) return "Microsoft Edge";
    if (ua.includes("curl") || ua.includes("python") || ua.includes("nexus-cli")) return "Nexus Terminal CLI";
    return ua.slice(0, 30);
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Linked Devices &amp; Login Sessions</h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Inspect hardware nodes registered to your account and review active Nexus cryptographic sessions.
        </p>
      </div>

      {/* Critical Scope Clarification Notice */}
      <Card className="border-sky-500/20 bg-sky-950/20">
        <CardContent className="p-4 flex items-start gap-3">
          <Info className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
          <div className="text-xs text-slate-300 leading-relaxed">
            <strong className="text-white">Notice regarding OAuth &amp; Sessions:</strong> The sessions listed below
            are cryptographic authentication tokens issued strictly for access to your <strong>NEXUS account</strong>.
            In compliance with zero-trust privacy boundaries, Google OAuth does not grant NEXUS authority to inspect or
            manage your general Google account sessions across Google search, Gmail, or other Google services.
          </div>
        </CardContent>
      </Card>

      {/* Section 1: Linked Client Devices */}
      <Card className="border-white/8 bg-[#0d131f]/70">
        <CardHeader className="p-5 border-b border-white/5">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base text-white">Registered Client Devices</CardTitle>
              <CardDescription className="text-xs text-slate-400">
                Authorized hardware nodes permitted to pair and sync data through your account.
              </CardDescription>
            </div>
            <Badge variant="outline" className="border-sky-500/20 text-sky-400 font-mono text-xs">
              {devices.length} {devices.length === 1 ? "Node" : "Nodes"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loadingDevices ? (
            <div className="p-8 text-center text-xs text-slate-500 animate-pulse">Loading devices...</div>
          ) : devices.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No hardware devices currently registered. Pair a desktop or mobile node using the CLI or companion app.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-white/5 bg-white/[0.01] text-slate-400 font-mono text-[11px]">
                    <th className="p-3.5 pl-5">Device Name</th>
                    <th className="p-3.5">Platform</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5">Registered</th>
                    <th className="p-3.5">Last Seen</th>
                    <th className="p-3.5 text-right pr-5">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-slate-300">
                  {devices.map((device) => (
                    <tr key={device.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="p-3.5 pl-5 font-semibold text-white flex items-center gap-2.5">
                        {getPlatformIcon(device.platform)}
                        <span>{device.name}</span>
                      </td>
                      <td className="p-3.5 uppercase font-mono text-[11px] text-slate-400">
                        {device.platform}
                      </td>
                      <td className="p-3.5">
                        {device.is_online ? (
                          <span className="inline-flex items-center gap-1.5 text-emerald-400 font-mono text-[11px]">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                            ONLINE
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 text-slate-500 font-mono text-[11px]">
                            <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
                            OFFLINE
                          </span>
                        )}
                      </td>
                      <td className="p-3.5 text-slate-400 text-[11px]">{formatDate(device.registered_at)}</td>
                      <td className="p-3.5 text-slate-400 text-[11px]">{formatDate(device.last_seen)}</td>
                      <td className="p-3.5 text-right pr-5">
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => setDeviceToRevoke(device)}
                          className="h-7 text-[11px] px-2.5"
                        >
                          <Trash2 className="w-3 h-3 mr-1" />
                          Revoke
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Section 2: Nexus Login Sessions */}
      <Card className="border-white/8 bg-[#0d131f]/70">
        <CardHeader className="p-5 border-b border-white/5">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base text-white">Active Login Sessions</CardTitle>
              <CardDescription className="text-xs text-slate-400">
                Sovereign authentication tokens issued for this identity with token family rotation tracking.
              </CardDescription>
            </div>
            <Badge variant="outline" className="border-emerald-500/20 text-emerald-400 font-mono text-xs">
              {sessions.filter((s) => !s.revoked_at && new Date(s.expires_at) > new Date()).length} Active
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loadingSessions ? (
            <div className="p-8 text-center text-xs text-slate-500 animate-pulse">Loading session records...</div>
          ) : sessions.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">No active login sessions found.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-white/5 bg-white/[0.01] text-slate-400 font-mono text-[11px]">
                    <th className="p-3.5 pl-5">Session / Client</th>
                    <th className="p-3.5">Method</th>
                    <th className="p-3.5">IP Address</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5">Issued</th>
                    <th className="p-3.5">Expires</th>
                    <th className="p-3.5 text-right pr-5">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-slate-300">
                  {sessions.map((sess) => {
                    const isRevoked = Boolean(sess.revoked_at);
                    const isExpired = new Date(sess.expires_at) < new Date();
                    const isActive = !isRevoked && !isExpired;

                    return (
                      <tr key={sess.id} className="hover:bg-white/[0.02] transition-colors">
                        <td className="p-3.5 pl-5">
                          <div className="font-semibold text-white flex items-center gap-2">
                            <KeyRound className="w-3.5 h-3.5 text-sky-400" />
                            <span>{parseUserAgent(sess.user_agent)}</span>
                          </div>
                          <span className="text-[10px] font-mono text-slate-500 block mt-0.5">
                            Session #{sess.id}
                          </span>
                        </td>
                        <td className="p-3.5 font-mono text-[11px]">
                          <Badge variant="outline" className="border-white/10 text-slate-300 text-[10px] uppercase">
                            {sess.created_via}
                          </Badge>
                        </td>
                        <td className="p-3.5 font-mono text-[11px] text-slate-400">
                          {sess.last_used_ip || "Internal/Local"}
                        </td>
                        <td className="p-3.5">
                          {isActive ? (
                            <span className="inline-flex items-center gap-1.5 text-emerald-400 font-mono text-[11px]">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              ACTIVE
                            </span>
                          ) : isRevoked ? (
                            <span className="inline-flex items-center gap-1.5 text-rose-400 font-mono text-[11px]">
                              <XCircle className="w-3.5 h-3.5" />
                              REVOKED
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 text-slate-500 font-mono text-[11px]">
                              <Clock className="w-3.5 h-3.5" />
                              EXPIRED
                            </span>
                          )}
                        </td>
                        <td className="p-3.5 text-slate-400 text-[11px]">{formatDate(sess.issued_at)}</td>
                        <td className="p-3.5 text-slate-400 text-[11px]">{formatDate(sess.expires_at)}</td>
                        <td className="p-3.5 text-right pr-5">
                          {isActive ? (
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => setSessionToRevoke(sess)}
                              className="h-7 text-[11px] px-2.5"
                            >
                              Revoke
                            </Button>
                          ) : (
                            <span className="text-[10px] text-slate-600 font-mono">Inactivated</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Confirmation Modal: Revoke Device */}
      <Modal
        isOpen={Boolean(deviceToRevoke)}
        onClose={() => {
          setDeviceToRevoke(null);
          setActionError(null);
        }}
        title="Revoke Device Access"
        description="Are you sure you want to disconnect and revoke this hardware node?"
      >
        <div className="space-y-4">
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
            <p className="font-semibold flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 text-rose-400" />
              Confirmation Required
            </p>
            <p className="mt-1 text-slate-300">
              Revoking <strong className="text-white">{deviceToRevoke?.name}</strong> will terminate its pairing code,
              disconnect its relay socket, and require re-authentication.
            </p>
          </div>

          {actionError && <p className="text-xs text-rose-400 font-mono">{actionError}</p>}

          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="outline"
              onClick={() => {
                setDeviceToRevoke(null);
                setActionError(null);
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deviceToRevoke && revokeDeviceMutation.mutate(deviceToRevoke.id)}
              disabled={revokeDeviceMutation.isPending}
            >
              {revokeDeviceMutation.isPending ? "Revoking..." : "Confirm Revocation"}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Confirmation Modal: Revoke Session */}
      <Modal
        isOpen={Boolean(sessionToRevoke)}
        onClose={() => {
          setSessionToRevoke(null);
          setActionError(null);
        }}
        title="Revoke Session Token"
        description="Are you sure you want to revoke this authentication session?"
      >
        <div className="space-y-4">
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
            <p className="font-semibold flex items-center gap-1.5">
              <ShieldAlert className="w-4 h-4 text-rose-400" />
              Token Family Invalidation
            </p>
            <p className="mt-1 text-slate-300">
              Revoking Session <strong className="text-white">#{sessionToRevoke?.id}</strong> will immediately invalidate
              its entire refresh token lineage. Any client relying on this token will be forced to log in again.
            </p>
          </div>

          {actionError && <p className="text-xs text-rose-400 font-mono">{actionError}</p>}

          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="outline"
              onClick={() => {
                setSessionToRevoke(null);
                setActionError(null);
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => sessionToRevoke && revokeSessionMutation.mutate(sessionToRevoke.id)}
              disabled={revokeSessionMutation.isPending}
            >
              {revokeSessionMutation.isPending ? "Revoking..." : "Confirm Revocation"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
