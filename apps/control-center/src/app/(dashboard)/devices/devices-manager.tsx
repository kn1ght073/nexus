"use client";

import React, { useState, useMemo } from "react";
import {
  Laptop,
  Server,
  Plus,
  Trash2,
  Search,
  Key,
  CheckCircle2,
  XCircle,
  Copy,
  Terminal,
  Activity,
  Layers,
} from "lucide-react";
import { DeviceRecord, NodeRecord } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Modal } from "@/components/ui/modal";
import { formatDate } from "@/lib/utils";

interface DevicesManagerProps {
  initialDevices: DeviceRecord[];
  initialNodes: NodeRecord[];
}

export function DevicesManager({ initialDevices, initialNodes }: DevicesManagerProps) {
  const [devices, setDevices] = useState<DeviceRecord[]>(initialDevices);
  const [nodes, setNodes] = useState<NodeRecord[]>(initialNodes);
  const [activeTab, setActiveTab] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);

  // New device form state
  const [deviceName, setDeviceName] = useState("");
  const [platform, setPlatform] = useState<string>("windows");
  const [capabilities, setCapabilities] = useState("sync,devices");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Filtered devices
  const filteredDevices = useMemo(() => {
    return devices.filter((dev) => {
      const matchesTab = activeTab === "all" || dev.platform.toLowerCase() === activeTab;
      const matchesSearch =
        dev.name.toLowerCase().includes(search.toLowerCase()) ||
        dev.capabilities.some((c) => c.toLowerCase().includes(search.toLowerCase()));
      return matchesTab && matchesSearch;
    });
  }, [devices, activeTab, search]);

  const handleRegisterDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);

    try {
      const capsArray = capabilities
        .split(",")
        .map((c) => c.trim())
        .filter(Boolean);

      const res = await fetch("/api/devices", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: deviceName,
          platform,
          capabilities: capsArray,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to register device");

      setDevices([data, ...devices]);
      setDeviceName("");
      setModalOpen(false);
    } catch (err: any) {
      setFormError(err.message || "Failed to register device");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteDevice = async (id: number) => {
    if (!confirm("Are you sure you want to revoke and delete this registered device?")) return;
    try {
      const res = await fetch(`/api/devices/${id}`, { method: "DELETE" });
      if (res.ok) {
        setDevices(devices.filter((d) => d.id !== id));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const platforms = [
    { id: "all", label: "All Platforms" },
    { id: "windows", label: "Windows" },
    { id: "macos", label: "macOS" },
    { id: "android", label: "Android" },
    { id: "linux", label: "Linux" },
    { id: "cli", label: "CLI" },
  ];

  return (
    <div className="space-y-8">
      {/* Header and Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <Laptop className="w-5 h-5 text-sky-400" />
            DEVICES & FLEET
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Enroll user endpoints, issue capability tokens, and coordinate distributed main server nodes.
          </p>
        </div>

        <Button onClick={() => setModalOpen(true)} className="text-xs h-9 font-semibold">
          <Plus className="w-4 h-4 mr-1.5" />
          Enroll New Device
        </Button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 p-2 bg-[#0c1220]/70 border border-white/8 rounded-xl">
        {/* Platform tabs */}
        <div className="flex items-center gap-1 overflow-x-auto pb-1 md:pb-0">
          {platforms.map((p) => (
            <button
              key={p.id}
              onClick={() => setActiveTab(p.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap cursor-pointer ${
                activeTab === p.id
                  ? "bg-sky-500/20 text-sky-400 border border-sky-500/30"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative w-full md:w-64">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
          <Input
            placeholder="Search by name or capability..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 h-8 text-xs bg-black/40"
          />
        </div>
      </div>

      {/* Devices Table */}
      <div className="rounded-xl border border-white/8 bg-[#0c1220]/70 overflow-hidden shadow-xl">
        <div className="p-4 border-b border-white/8 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-sky-400" />
            <h2 className="text-xs font-semibold tracking-wider text-white">REGISTERED ENDPOINTS</h2>
          </div>
          <span className="text-xs text-slate-400 font-mono">{filteredDevices.length} matching</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-black/30 border-b border-white/8 text-slate-400 uppercase tracking-wider font-mono text-[10px]">
              <tr>
                <th className="py-3 px-4">Device Name</th>
                <th className="py-3 px-4">Platform</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Capabilities</th>
                <th className="py-3 px-4">Registered / Last Seen</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              {filteredDevices.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No devices found matching your criteria.
                  </td>
                </tr>
              ) : (
                filteredDevices.map((dev) => (
                  <tr key={dev.id} className="hover:bg-white/5 transition-colors">
                    <td className="py-3 px-4 font-medium text-white flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-sky-400" />
                      <span>{dev.name}</span>
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant="outline" className="font-mono text-[10px] uppercase">
                        {dev.platform}
                      </Badge>
                    </td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center gap-1.5 font-mono text-[11px]">
                        {dev.is_online ? (
                          <>
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                            <span className="text-emerald-400">Online</span>
                          </>
                        ) : (
                          <>
                            <XCircle className="w-3.5 h-3.5 text-slate-500" />
                            <span className="text-slate-500">Offline</span>
                          </>
                        )}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex flex-wrap gap-1">
                        {dev.capabilities?.map((cap) => (
                          <Badge
                            key={cap}
                            variant="secondary"
                            className="text-[9px] font-mono px-1.5 py-0 bg-white/5 text-slate-300"
                          >
                            {cap}
                          </Badge>
                        ))}
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                      <div>Seen: {formatDate(dev.last_seen)}</div>
                      <div className="text-slate-500 text-[10px]">Reg: {formatDate(dev.registered_at)}</div>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleDeleteDevice(dev.id)}
                        className="p-1.5 text-slate-500 hover:text-rose-400 transition-colors cursor-pointer"
                        title="Revoke device"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Nodes Section */}
      <div className="rounded-xl border border-white/8 bg-[#0c1220]/70 overflow-hidden shadow-xl">
        <div className="p-4 border-b border-white/8 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-amber-400" />
            <h2 className="text-xs font-semibold tracking-wider text-white">COORDINATED SERVER NODES</h2>
          </div>
          <Badge variant="outline" className="text-[10px] font-mono text-amber-400 border-amber-500/30">
            {nodes.length} CLAIMED
          </Badge>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-black/30 border-b border-white/8 text-slate-400 uppercase tracking-wider font-mono text-[10px]">
              <tr>
                <th className="py-3 px-4">Node Name</th>
                <th className="py-3 px-4">Platform</th>
                <th className="py-3 px-4">LAN IP / Endpoint</th>
                <th className="py-3 px-4">Liveness</th>
                <th className="py-3 px-4">Last Heartbeat</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-300">
              {nodes.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    No nodes claimed yet. Use the CLI instruction below to claim a main node.
                  </td>
                </tr>
              ) : (
                nodes.map((node) => (
                  <tr key={node.id} className="hover:bg-white/5 transition-colors">
                    <td className="py-3 px-4 font-medium text-white flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-amber-400" />
                      <span>{node.name}</span>
                    </td>
                    <td className="py-3 px-4 font-mono uppercase text-[10px]">{node.platform}</td>
                    <td className="py-3 px-4 font-mono text-sky-400">
                      {node.endpoint || node.lan_ip || "127.0.0.1:8000"}
                    </td>
                    <td className="py-3 px-4">
                      <Badge
                        variant={node.is_online ? "success" : "secondary"}
                        className="text-[9px] font-mono"
                      >
                        {node.is_online ? "ALIVE" : "STALE"}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-400 text-[11px]">
                      {node.last_seen ? formatDate(node.last_seen) : "Never"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Node Claim Guide */}
        <div className="p-4 bg-black/40 border-t border-white/8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-3">
            <Terminal className="w-5 h-5 text-sky-400 shrink-0" />
            <div>
              <p className="font-semibold text-white">How to claim a Node as Main Server</p>
              <p className="text-slate-400 text-[11px]">
                Run this command on your Mac or Windows machine to delegate local storage and services:
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 bg-slate-950 px-3 py-2 rounded-lg border border-white/10 font-mono text-sky-400 text-xs">
            <span>nexus node claim --watch</span>
          </div>
        </div>
      </div>

      {/* Modal: Enroll Device */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Enroll New Device"
        description="Add a device to your authorized fleet to receive synchronization and capability tokens."
      >
        <form onSubmit={handleRegisterDevice} className="space-y-4">
          {formError && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
              {formError}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Device Name</label>
            <Input
              required
              placeholder="e.g. Work-MacBook-Pro or Office-Desktop"
              value={deviceName}
              onChange={(e) => setDeviceName(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Platform</label>
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="w-full h-9 rounded-md border border-white/10 bg-white/5 px-3 py-1 text-xs text-white focus:outline-none focus:ring-1 focus:ring-sky-400"
            >
              <option value="windows" className="bg-[#0d1322]">
                Windows
              </option>
              <option value="macos" className="bg-[#0d1322]">
                macOS
              </option>
              <option value="android" className="bg-[#0d1322]">
                Android
              </option>
              <option value="linux" className="bg-[#0d1322]">
                Linux
              </option>
              <option value="cli" className="bg-[#0d1322]">
                CLI
              </option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Capabilities (comma separated)</label>
            <Input
              value={capabilities}
              onChange={(e) => setCapabilities(e.target.value)}
              placeholder="sync, devices, admin"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Registering..." : "Enroll Device"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
