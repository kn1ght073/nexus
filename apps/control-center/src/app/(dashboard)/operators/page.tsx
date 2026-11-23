import { coreApi } from "@/lib/api-server";
import { OperatorsManager } from "./operators-manager";
import { ShieldAlert } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function OperatorsPage() {
  const { data: currentUser } = await coreApi.getCurrentUser();

  if (!currentUser || (currentUser.role !== "owner" && currentUser.role !== "operator")) {
    return (
      <div className="py-16 text-center space-y-4">
        <div className="w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 mx-auto grid place-items-center">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <h1 className="text-lg font-bold text-white">ACCESS RESTRICTED</h1>
        <p className="text-xs text-slate-400 max-w-sm mx-auto">
          Operator management requires elevated operator or owner privileges. Your current role is{" "}
          <span className="font-mono text-sky-400 uppercase">{currentUser?.role || "user"}</span>.
        </p>
      </div>
    );
  }

  const { data: users } = await coreApi.getUsers();

  return <OperatorsManager currentUser={currentUser} initialUsers={users || []} />;
}
