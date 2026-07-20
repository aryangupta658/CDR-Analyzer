import { Outlet } from "react-router";

import Navbar from "./Navbar";

export default function PublicLayout() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      <Outlet />
    </div>
  );
}
