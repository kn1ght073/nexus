"use client";

import React, { useState, useMemo } from "react";
import { FileText, Download, Search, Filter, Clock, Tag } from "lucide-react";
import { ActivityRecord } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

interface AuditViewerProps {
  initialActivity: ActivityRecord[];
}

export function AuditViewer({ initialActivity }: AuditViewerProps) {
  const [activity, setActivity] = useState<ActivityRecord[]>(initialActivity);
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("all");

  const filteredLogs = useMemo(() => {
    return activity.filter((item) => {
      const matchesAction =
        actionFilter === "all" || item.action.toLowerCase().startsWith(actionFilter);
      const matchesSearch =
        item.action.toLowerCase().includes(search.toLowerCase()) ||
        item.detail.toLowerCase().includes(search.toLowerCase());
      return matchesAction && matchesSearch;
    });
  }, [activity, actionFilter, search]);

  const handleExportJSON = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(filteredLogs, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `nexus-audit-logs-${new Date().toISOString()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const categories = [
    { id: "all", label: "All Actions" },
    { id: "auth", label: "Auth & Sessions" },
    { id: "device", label: "Devices" },
    { id: "node", label: "Nodes" },
    { id: "user", label: "Users & Roles" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-white/8">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <FileText className="w-5 h-5 text-sky-400" />
            AUDIT LOGS & PROVENANCE
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Tamper-evident operational event stream tracking all authenticated actions and node modifications.
          </p>
        </div>

        <Button onClick={handleExportJSON} variant="outline" className="text-xs h-9">
          <Download className="w-4 h-4 mr-1.5" />
          Export JSON Audit
        </Button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 p-2 bg-[#0c1220]/70 border border-white/8 rounded-xl">
        <div className="flex items-center gap-1 overflow-x-auto pb-1 md:pb-0">
          {categories.map((c) => (
            <button
              key={c.id}
              onClick={() => setActionFilter(c.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap cursor-pointer ${
                actionFilter === c.id
                  ? "bg-sky-500/20 text-sky-400 border border-sky-500/30"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        <div className="relative w-full md:w-64">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
          <Input
            placeholder="Search action or detail..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 h-8 text-xs bg-black/40"
          />
        </div>
      </div>

      {/* Activity Table */}
      <div className="rounded-xl border border-white/8 bg-[#0c1220]/70 overflow-hidden shadow-xl">
        <div className="p-4 border-b border-white/8 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-sky-400" />
            <h2 className="text-xs font-semibold tracking-wider text-white">EVENT LOG STREAM</h2>
          </div>
          <span className="text-xs text-slate-400 font-mono">{filteredLogs.length} events logged</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-black/30 border-b border-white/8 text-slate-400 uppercase tracking-wider font-mono text-[10px]">
              <tr>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4">Actor / Device</th>
                <th className="py-3 px-4">Event Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-slate-500">
                    No audit records matching criteria.
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-white/5 transition-colors">
                    <td className="py-3 px-4 font-mono text-slate-400 text-[11px] whitespace-nowrap">
                      {formatDate(log.created_at)}
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant="outline" className="font-mono text-[10px] text-sky-400 border-sky-500/20">
                        {log.action}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-300">
                      {log.user_id && <span className="text-slate-400">UID #{log.user_id} </span>}
                      {log.device_id && (
                        <span className="text-indigo-400">[Dev #{log.device_id}]</span>
                      )}
                      {!log.user_id && !log.device_id && <span className="text-slate-500">System</span>}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-300 max-w-md break-all">
                      {log.detail || "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
