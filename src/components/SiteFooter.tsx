import { Brand } from "./Brand";
import type { View } from "../types";

export function SiteFooter({ setView }: { setView: (view: View) => void }) {
  const go = (view: View) => {
    setView(view);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
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
          <p>Barranquilla, Colombia</p>
          <p><a href="https://wa.me/573014474936" target="_blank" rel="noopener noreferrer">+57 301 447 4936</a></p>
          <p><a href="mailto:oleajecolombia@gmail.com">oleajecolombia@gmail.com</a></p>
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
        <span>© {new Date().getFullYear()} Oleaje. Hecho en Colombia.</span>
        <span>Privacidad &nbsp; · &nbsp; Términos</span>
      </div>
    </footer>
  );
}
