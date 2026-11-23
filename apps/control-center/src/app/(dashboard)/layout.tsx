import { redirect } from "next/navigation";
import { coreApi } from "@/lib/api-server";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { data: user, error } = await coreApi.getCurrentUser();

  if (!user || error) {
    redirect("/login");
  }

  // Regular users are segregated strictly into the Client Console
  if (user.role === "user") {
    redirect("/client");
  }

  return (
    <div className="flex min-h-screen bg-[#080b11]">
      <Sidebar user={user} />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 p-6 overflow-y-auto max-w-7xl w-full mx-auto">{children}</main>
      </div>
    </div>
  );
}
