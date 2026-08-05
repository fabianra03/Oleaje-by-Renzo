import logo from "../assets/oleaje-logo.png";

export function Brand({ inverse = false }: { inverse?: boolean }) {
  return (
    <img
      className={`brand-logo${inverse ? " inverse" : ""}`}
      src={logo}
      alt="Oleaje"
    />
  );
}
