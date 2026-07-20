import { BarChart3, Menu, X } from "lucide-react";
import { useState } from "react";
import { Link, NavLink } from "react-router";

export default function Navbar() {
  const [open, setOpen] = useState(false);

  const links = [
    {
      label: "Home",
      to: "/",
    },
    {
      label: "Features",
      to: "/#features",
    },
    {
      label: "How It Works",
      to: "/#how-it-works",
    },
  ];

  return (
    <header className="border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-2">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-50 text-orange-500">
            <BarChart3 size={23} />
          </span>

          <span className="font-bold text-slate-950">CDR Analyzer</span>
        </Link>

        <nav className="hidden items-center gap-7 md:flex">
          {links.map((link) => (
            <NavLink
              key={link.label}
              to={link.to}
              className="text-sm font-medium text-slate-600 hover:text-blue-600"
            >
              {link.label}
            </NavLink>
          ))}

          <Link
            to="/login"
            className="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
          >
            Login
          </Link>
        </nav>

        <button
          className="rounded-lg p-2 md:hidden"
          onClick={() => setOpen(!open)}
          aria-label="Open navigation"
        >
          {open ? <X /> : <Menu />}
        </button>
      </div>

      {open && (
        <nav className="space-y-2 border-t border-slate-200 bg-white p-4 md:hidden">
          {links.map((link) => (
            <NavLink
              key={link.label}
              to={link.to}
              onClick={() => setOpen(false)}
              className="block rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              {link.label}
            </NavLink>
          ))}

          <Link
            to="/login"
            onClick={() => setOpen(false)}
            className="block rounded-lg bg-blue-600 px-3 py-2 text-center text-sm font-semibold text-white"
          >
            Login
          </Link>
        </nav>
      )}
    </header>
  );
}
