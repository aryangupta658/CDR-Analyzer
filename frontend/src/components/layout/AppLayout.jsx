import { useState } from "react";
import { Outlet } from "react-router";

import { useAuth } from "../../context/AuthContext";
import Sidebar, { MobileMenuButton } from "./Sidebar";

export default function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);

  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:px-6">
          <MobileMenuButton onClick={() => setMobileOpen(true)} />

          <div className="ml-auto flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-semibold text-slate-900">
                {user?.full_name || user?.username || "Investigator"}
              </p>

              <p className="text-xs text-slate-500">Investigator</p>
            </div>

            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 font-semibold text-white">
              {(user?.full_name || user?.username || "I")
                .charAt(0)
                .toUpperCase()}
            </div>
          </div>
        </header>

        <main className="p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
