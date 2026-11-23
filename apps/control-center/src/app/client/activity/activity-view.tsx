"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  History,
  KeyRound,
  Laptop,
  Shield,
  Filter,
  ChevronLeft,
  ChevronRight,
  Clock,
  UserCheck,
  Radio,
  FileText,
} from "lucide-react";
import { ActivityPage } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";

export function ClientActivityView() {
  const [category, setCategory] = useState<string>("all");
  const [page, setPage] = useState<number>(0);
  const limit = 20;

  const { data, isLoading } = useQuery<ActivityPage>({
    queryKey: ["client-activity", category, page],
    queryFn: async () => {
      const params = new URLSearchParams({
        limit: String(limit),
        offset: String(page * limit),
      });
      if (category !== "all") {
        params.set("category", category);
      }
      const res = await fetch(`/api/account/activity?${params.toString()}`);
      if (!res.ok) throw new Error("Failed to load activity");
      return res.json();
    },
  });

  const getEventIcon = (action: string) => {
    if (action.includes("login") || action.includes("auth")) {
      return <KeyRound className="w-4 h-4 text-emerald-400" />;
    }
    if (action.includes("device")) {
      return <Laptop className="w-4 h-4 text-sky-400" />;
    }
    if (action.includes("relay") || action.includes("socket")) {
      return <Radio className="w-4 h-4 text-purple-400" />;
    }
    if (action.includes("role") || action.includes("user")) {
      return <UserCheck className="w-4 h-4 text-amber-400" />;
    }
    return <FileText className="w-4 h-4 text-slate-400" />;
  };

  const getCategoryBadge = (action: string) => {
    if (action.startsWith("user.") || action.startsWith("auth.")) {
      return <Badge variant="outline" className="border-emerald-500/30 text-emerald-400 text-[10px]">AUTH</Badge>;
    }
    if (action.startsWith("device.")) {
      return <Badge variant="outline" className="border-sky-500/30 text-sky-400 text-[10px]">DEVICE</Badge>;
    }
    return <Badge variant="outline" className="border-white/10 text-slate-400 text-[10px]">SECURITY</Badge>;
  };

  const items = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / limit) || 1;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Account Activity Timeline</h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Immutable audit record of all authentication events, device actions, and session state changes.
        </p>
      </div>

      {/* Filter and Metrics Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-[#0d131f]/70 border border-white/8 rounded-xl p-4">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-mono text-slate-400 mr-2 flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-sky-400" />
            FILTER:
          </span>
          {[
            { id: "all", label: "All Activity" },
            { id: "auth", label: "Logins & Tokens" },
            { id: "device", label: "Hardware Nodes" },
            { id: "session", label: "Sessions" },
          ].map((cat) => (
            <button
              key={cat.id}
              onClick={() => {
                setCategory(cat.id);
                setPage(0);
              }}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                category === cat.id
                  ? "bg-sky-500/20 text-sky-400 border border-sky-500/30 font-semibold"
                  : "bg-white/5 text-slate-400 hover:text-white border border-white/5"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        <span className="text-xs font-mono text-slate-400">
          Showing <span className="text-white font-semibold">{total}</span> total events
        </span>
      </div>

      {/* Timeline Stream */}
      <Card className="border-white/8 bg-[#0d131f]/70">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-12 text-center text-xs text-slate-500 animate-pulse">Loading activity stream...</div>
          ) : items.length === 0 ? (
            <div className="p-12 text-center text-xs text-slate-500">
              No activity logs recorded under this filter.
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {items.map((event) => (
                <div
                  key={event.id}
                  className="p-4 sm:px-6 hover:bg-white/[0.02] transition-colors flex items-start gap-4"
                >
                  <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 grid place-items-center shrink-0 mt-0.5">
                    {getEventIcon(event.action)}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-xs text-white font-mono">{event.action}</span>
                      {getCategoryBadge(event.action)}
                      <span className="text-[10px] text-slate-500 font-mono">#{event.id}</span>
                    </div>

                    <p className="text-xs text-slate-300 mt-1 break-words font-mono bg-black/20 p-2 rounded border border-white/5">
                      {event.detail || "Action completed successfully."}
                    </p>

                    <div className="flex items-center gap-1.5 mt-2 text-[11px] text-slate-500 font-mono">
                      <Clock className="w-3 h-3 text-slate-500" />
                      <span>{formatDate(event.created_at)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pagination Controls */}
      <div className="flex items-center justify-between py-2 text-xs text-slate-400">
        <span>
          Page <strong className="text-white">{page + 1}</strong> of <strong className="text-white">{totalPages}</strong>
        </span>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0 || isLoading}
            className="h-8 text-xs gap-1"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => p + 1)}
            disabled={page + 1 >= totalPages || isLoading}
            className="h-8 text-xs gap-1"
          >
            Next
            <ChevronRight className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
