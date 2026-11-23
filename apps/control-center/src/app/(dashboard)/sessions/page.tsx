import { coreApi } from "@/lib/api-server";
import { SessionsManager } from "./sessions-manager";

export const dynamic = "force-dynamic";

export default async function SessionsPage() {
  const { data: sessions } = await coreApi.getSessions();
  return <SessionsManager initialSessions={sessions || []} />;
}
