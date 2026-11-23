import { coreApi } from "@/lib/api-server";
import { DevicesManager } from "./devices-manager";

export const dynamic = "force-dynamic";

export default async function DevicesPage() {
  const [devRes, nodeRes] = await Promise.all([
    coreApi.getDevices(),
    coreApi.getNodes(),
  ]);

  const devices = devRes.data || [];
  const nodes = nodeRes.data || [];

  return <DevicesManager initialDevices={devices} initialNodes={nodes} />;
}
