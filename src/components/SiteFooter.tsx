import { Brand } from "./Brand";
import type { View } from "../types";

type AppConfig = {
  whatsapp: string;
  email: string;
  brand: string;
  city: string;
};

export function SiteFooter({
  setView,
  config,
}: {
  setView: (view: View) => void;
  config: AppConfig;
}) {
  const go = (view: View) => {
    setView(view);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const whatsappHref = config.whatsapp ? `https://wa.me/${config.whatsapp}` : "#";
  const emailHref = config.email ? `mailto:${config.email}` : "#";

  return (
    <footer className="site-footer">
      <div className="footer-top">
        <div className="footer-brand">
          <Brand inverse />
          <p>Objetos tejidos con calma, hechos para acompañar tus días.</p>
          <div className="socials">
            <a href="https://www.instagram.com/oleaje_col?igsh=Nnk1cHk3amo1ZTZ1&utm_source=qr" target="_blank" rel="noopener noreferrer">ig</a>
            <a href="#facebook">f</a>
          </div>
        </div>
        <div>
          <h4>Explora</h4>
          <button onClick={() => go("inicio")}>Nuestra historia</button>
          <button onClick={() => go("productos")}>Colección</button>
          <button onClick={() => go("contacto")}>Regalos especiales</button>
        </div>
        <div>
          <h4>Estamos cerca</h4>
          <p>{config.city || "Barranquilla, Colombia"}</p>
          {config.whatsapp && (
            <p><a href={whatsappHref} target="_blank" rel="noopener noreferrer">{whatsappHref.replace("https://wa.me/", "+")}</a></p>
          )}
          {config.email && (
            <p><a href={emailHref}>{config.email}</a></p>
          )}
        </div>
        <div>
          <h4>Despacio es mejor</h4>
          <p>
            Recibe historias, lanzamientos y piezas que celebran lo hecho a
            mano.
          </p>
          <button className="footer-newsletter" onClick={() => go("contacto")}>
            Quiero recibirlas →
          </button>
        </div>
      </div>
      <div className="footer-bottom">
        <span>© {new Date().getFullYear()} {config.brand || "Oleaje"}. Hecho en Colombia.</span>
        <span>Privacidad &nbsp; · &nbsp; Términos</span>
      </div>
    </footer>
  );
}
