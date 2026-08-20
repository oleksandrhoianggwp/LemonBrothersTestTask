import type { PropsWithChildren } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export function Layout({ children }: PropsWithChildren) {
  const { logout } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink className="brand" to="/dashboard">
          <span className="brand-mark">LB</span>
          <span>
            <strong>Lemon Brothers</strong>
            <small>Product intelligence</small>
          </span>
        </NavLink>
        <nav>
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/sales-boost">Sales Boost</NavLink>
          <button
            className="button button-ghost"
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Sign out
          </button>
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
