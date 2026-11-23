import { coreApi } from "@/lib/api-server";
import { AuditViewer } from "./audit-viewer";

export const dynamic = "force-dynamic";

export default async function AuditPage() {
  const { data: activity } = await coreApi.getActivity(100);
  return <AuditViewer initialActivity={activity || []} />;
}
