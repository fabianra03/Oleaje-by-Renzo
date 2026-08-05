import { useState } from "react";
import type { View } from "../types";
import { Brand } from "./Brand";

const links: { label: string; view: View }[] = [
  { label: "Inicio", view: "inicio" },
  { label: "Colección", view: "productos" },
  { label: "Contacto", view: "contacto" },
];

export function SiteHeader({
  view,
  setView,
}: {
  view: View;
  setView: (view: View) => void;
}) {
  const [open, setOpen] = useState(false);
  const navigate = (next: View) => {
    setView(next);
    setOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  return (
    <header className="site-header">
      <div className="nav-shell">
        <button className="brand-button" onClick={() => navigate("inicio")}>
          <Brand />
        </button>
        <button
          className="menu-toggle"
          onClick={() => setOpen(!open)}
          aria-label="Abrir menú"
        >
          {open ? "×" : "☰"}
        </button>
        <nav className={open ? "open" : ""}>
          {links.map((link) => (
            <button
              key={link.view}
              className={view === link.view ? "active" : ""}
              onClick={() => navigate(link.view)}
            >
              {link.label}
            </button>
          ))}
          <button className="admin-link" onClick={() => navigate("admin")}>
            Administrar
          </button>
        </nav>
      </div>
    </header>
  );
}
