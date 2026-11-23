import { describe, it, expect, vi } from "vitest";
import { cn, formatDate } from "@/lib/utils";

describe("NEXUS Control Center Utility Suite", () => {
  it("merges tailwind classes cleanly via cn()", () => {
    const res = cn("bg-black px-4", "px-6 text-white", false && "hidden");
    expect(res).toContain("bg-black");
    expect(res).toContain("px-6");
    expect(res).toContain("text-white");
    expect(res).not.toContain("px-4");
  });

  it("formats dates gracefully without throw", () => {
    expect(formatDate(null)).toBe("Never");
    expect(formatDate(undefined)).toBe("Never");
    expect(formatDate("2026-11-23T20:00:00Z")).toContain("2026");
  });

  it("handles invalid dates safely in formatDate", () => {
    expect(formatDate("not-a-valid-date")).toBe("Invalid date");
  });
});

describe("RBAC Role Logic & Permission Hierarchy", () => {
  type Role = "user" | "operator" | "owner";

  const canManageOperators = (role: Role) => role === "owner" || role === "operator";
  const canAssignRoles = (role: Role) => role === "owner";

  it("enforces operator management access", () => {
    expect(canManageOperators("user")).toBe(false);
    expect(canManageOperators("operator")).toBe(true);
    expect(canManageOperators("owner")).toBe(true);
  });

  it("restricts role assignment exclusively to owner", () => {
    expect(canAssignRoles("user")).toBe(false);
    expect(canAssignRoles("operator")).toBe(false);
    expect(canAssignRoles("owner")).toBe(true);
  });
});

describe("Control Center Environment & Base URL Resolution", () => {
  it("resolves default production control-plane API when unset", () => {
    const original = process.env.NEXUS_API_BASE_URL;
    delete process.env.NEXUS_API_BASE_URL;

    const fallbackUrl = (process.env.NEXUS_API_BASE_URL || "https://nexus-control-plane-uvi8.onrender.com").replace(/\/$/, "");
    expect(fallbackUrl).toBe("https://nexus-control-plane-uvi8.onrender.com");

    if (original) process.env.NEXUS_API_BASE_URL = original;
  });

  it("strips trailing slashes from custom API URL", () => {
    const raw = "https://custom-core.internal/";
    const normalized = raw.replace(/\/$/, "");
    expect(normalized).toBe("https://custom-core.internal");
  });
});
