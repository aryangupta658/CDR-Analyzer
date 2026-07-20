import {
  BadgeAlert,
  BarChart3,
  BriefcaseBusiness,
  FileUp,
  LayoutDashboard,
  LogOut,
  MapPinned,
  Menu,
  PhoneCall,
  ShieldAlert,
  Smartphone,
  X,
} from "lucide-react";

import { NavLink, useNavigate } from "react-router";

import { toast } from "react-toastify";

import { useAuth } from "../../context/AuthContext";

import { useCase } from "../../context/CaseContext";

export default function Sidebar({ mobileOpen, setMobileOpen }) {
  const { logout } = useAuth();

  const { selectedCase, clearCase } = useCase();

  const navigate = useNavigate();

  const caseId = selectedCase?.id;

  const links = [
    {
      label: "Dashboard",
      icon: LayoutDashboard,

      to: caseId ? `/app/cases/${caseId}/dashboard` : "/app/cases",

      requiresCase: true,
    },

    {
      label: "Cases",
      icon: BriefcaseBusiness,
      to: "/app/cases",
      requiresCase: false,
    },

    {
      label: "Evidence Files",
      icon: FileUp,

      to: caseId ? `/app/cases/${caseId}/evidence` : "/app/cases",

      requiresCase: true,
    },

    {
      label: "Number Analysis",
      icon: PhoneCall,
      to: "/app/analysis/numbers",
      requiresCase: true,
    },

    {
      label: "Device Analysis",
      icon: Smartphone,
      to: "/app/analysis/devices",
      requiresCase: true,
    },

    {
      label: "Location Analysis",
      icon: MapPinned,
      to: "/app/analysis/locations",
      requiresCase: true,
    },

    {
      label: "Incident Analysis",
      icon: ShieldAlert,
      to: "/app/analysis/incidents",
      requiresCase: true,
    },

    {
      label: "Pattern Analysis",
      icon: BadgeAlert,
      to: "/app/analysis/fraud",
      requiresCase: true,
    },
  ];

  function handleNavigation(event, item) {
    if (item.requiresCase && !selectedCase) {
      event.preventDefault();

      toast.error("Create or open a case first.");

      navigate("/app/cases");
    }

    setMobileOpen(false);
  }

  function handleLogout() {
    clearCase();
    logout();

    window.location.href = "/login";
  }

  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-slate-950/30 lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-label="Close sidebar overlay"
        />
      )}

      <aside
        className={`
          fixed inset-y-0 left-0 z-40
          flex w-72 flex-col
          border-r border-slate-200
          bg-white transition-transform
          duration-200 lg:translate-x-0
          ${mobileOpen ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        {/* ==================================================
            Logo
        ================================================== */}

        <div className="flex h-16 items-center justify-between border-b border-slate-200 px-5">
          <div className="flex items-center gap-2">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-50 text-orange-500">
              <BarChart3 size={22} />
            </span>

            <span className="font-bold text-slate-950">CDR Analyzer</span>
          </div>

          <button
            type="button"
            className="rounded-lg p-2 lg:hidden"
            onClick={() => setMobileOpen(false)}
            aria-label="Close sidebar"
          >
            <X size={20} />
          </button>
        </div>

        {/* ==================================================
            Selected case information
        ================================================== */}

        {selectedCase && (
          <div className="border-b border-slate-200 px-4 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Current case
            </p>

            <p className="mt-1 truncate text-sm font-bold text-slate-900">
              {selectedCase.title}
            </p>

            <p className="mt-1 truncate text-xs text-blue-600">
              {selectedCase.case_number}
            </p>
          </div>
        )}

        {/* ==================================================
            Navigation links
        ================================================== */}

        <nav className="flex-1 space-y-1 overflow-y-auto p-4">
          {links.map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                key={item.label}
                to={item.to}
                onClick={(event) => handleNavigation(event, item)}
                className={({ isActive }) =>
                  `
                      flex items-center gap-3
                      rounded-xl px-3 py-3
                      text-sm font-medium
                      transition
                      ${
                        isActive
                          ? "bg-blue-50 text-blue-700"
                          : "text-slate-600 hover:bg-slate-50 hover:text-slate-950"
                      }
                    `
                }
              >
                <Icon size={19} />

                {item.label}
              </NavLink>
            );
          })}
        </nav>

        {/* ==================================================
            Logout
        ================================================== */}

        <div className="border-t border-slate-200 p-4">
          <button
            type="button"
            onClick={handleLogout}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium text-slate-600 hover:bg-red-50 hover:text-red-600"
          >
            <LogOut size={19} />
            Logout
          </button>
        </div>
      </aside>
    </>
  );
}

export function MobileMenuButton({ onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-lg border border-slate-200 bg-white p-2 lg:hidden"
      aria-label="Open sidebar"
    >
      <Menu size={20} />
    </button>
  );
}
