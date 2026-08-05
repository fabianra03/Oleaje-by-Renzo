import { useEffect, useState } from "react";
import "./App.css";
import { formatPrice } from "./data/products";
import type { Product, View } from "./types";
import { Brand } from "./components/Brand";
import { ProductCard } from "./components/ProductCard";
import { SiteHeader } from "./components/SiteHeader";
import { SiteFooter } from "./components/SiteFooter";
import oleajeLogo from "./assets/oleaje-logo.png";

type CartItem = Product & { quantity: number };
type AdminUser = { id: string; username: string; name: string };

type AppConfig = {
  whatsapp: string;
  email: string;
  brand: string;
  city: string;
};

const DEFAULT_CONFIG: AppConfig = {
  whatsapp: "",
  email: "",
  brand: "Oleaje",
  city: "Barranquilla, Colombia",
};

function useAppConfig(): AppConfig {
  const [config, setConfig] = useState<AppConfig>(DEFAULT_CONFIG);
  useEffect(() => {
    fetch("/api/config")
      .then((res) => (res.ok ? res.json() : null))
      .then((data: AppConfig | null) => {
        if (data) setConfig(data);
      })
      .catch(() => { /* usa defaults */ });
  }, []);
  return config;
}

function AdminLogin({
  onSuccess,
  onBack,
}: {
  onSuccess: (user: AdminUser) => void;
  onBack?: () => void;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = (await response.json()) as {
        message?: string;
        user?: AdminUser;
      };
      if (!response.ok || !data.user) {
        setError(data.message ?? "No fue posible iniciar sesión.");
        return;
      }
      onSuccess(data.user);
    } catch {
      setError("No fue posible conectar con el servicio de acceso.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="admin-login-page">
      <section className="admin-login-card">
        {onBack && (
          <button type="button" className="admin-back-button" onClick={onBack}>
            ← Volver al inicio
          </button>
        )}
        <p className="eyebrow">Área privada</p>
        <h1>
          Administrar <em>Oleaje.</em>
        </h1>
        <p className="admin-login-intro">
          Ingresa con las credenciales registradas para administrar el taller.
        </p>
        <form onSubmit={submit}>
          <label>
            Nombre de usuario
            <input
              autoComplete="username"
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
              placeholder="tu.usuario"
            />
          </label>
          <label>
            Contraseña
            <input
              autoComplete="current-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              placeholder="••••••••"
            />
          </label>
          {error && <p className="login-error" role="alert">{error}</p>}
          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? "Verificando…" : "Entrar a administrar"} <span>→</span>
          </button>
        </form>
      </section>
    </main>
  );
}

function Home({ setView }: { setView: (view: View) => void }) {
  return (
    <>
      <section className="hero-section">
        <div className="hero-photo" />
        <div className="hero-overlay" />
        <div className="hero-watermark">OLEAJE</div>
        <div className="hero-content">
          <h1>
            <img src={oleajeLogo} alt="Oleaje Logo" />
          </h1>
          <p className="hero-text">
            Piezas tejidas a mano que guardan la calidez de una historia y la
            libertad de la costa.
          </p>
          <button
            className="primary-button"
            onClick={() => setView("productos")}
          >
            Descubrir la colección <span>→</span>
          </button>
        </div>
        <div className="hero-note">HECHO A MANO · BARRANQUILLA</div>
      </section>

      <section className="craft-section">
        <div className="craft-copy">
          <p className="eyebrow light">Nuestra forma de hacer</p>
          <h2>
            De las manos
            <br />a <em>tu mundo.</em>
          </h2>
          <p>
            No hacemos producción en masa. Cada puntada es una decisión
            consciente, cada material fue elegido por su tacto y durabilidad.
          </p>
        </div>
        <div className="craft-image">
          <span>
            Oficio vivo
            <br />
            desde 2025
          </span>
        </div>
      </section>
    </>
  );
}

function Products({
  products,
  loading,
  openProduct,
  addToBag,
}: {
  products: Product[];
  loading: boolean;
  openProduct: (product: Product) => void;
  addToBag: (product: Product) => void;
}) {
  const [filter, setFilter] = useState<string>("Todos");
  // Build dynamic category list from products in DB
  const dynamicCategories = ["Todos", ...Array.from(new Set(products.map((p) => p.category))).sort()];
  const shown =
    filter === "Todos"
      ? products
      : products.filter((product) => product.category === filter);
  return (
    <main className="page products-page">
      <div className="page-heading">
        <p className="eyebrow">Hecho con intención</p>
        <h1>
          Nuestra <em>colección.</em>
        </h1>
        <p>Objetos que celebran los pequeños rituales de cada día.</p>
      </div>
      <div className="filter-row">
        {dynamicCategories.map((cat) => (
          <button
            className={filter === cat ? "selected" : ""}
            onClick={() => setFilter(cat)}
            key={cat}
          >
            {cat}
          </button>
        ))}
      </div>
      {loading ? (
        <p className="result-count">Cargando colección…</p>
      ) : shown.length === 0 ? (
        <p className="result-count">Aún no hay piezas publicadas.</p>
      ) : (
        <>
          <p className="result-count">{shown.length} piezas encontradas</p>
          <div className="product-grid all-products">
            {shown.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                onDetail={openProduct}
                onBuy={addToBag}
              />
            ))}
          </div>
        </>
      )}
    </main>
  );
}

function CartSummary({
  cartItems,
  removeFromCart,
  increaseQuantity,
  decreaseQuantity,
  setView,
  config,
}: {
  cartItems: CartItem[];
  removeFromCart: (productId: number) => void;
  increaseQuantity: (productId: number) => void;
  decreaseQuantity: (productId: number) => void;
  setView: (view: View) => void;
  config: AppConfig;
}) {
  const total = cartItems.reduce(
    (sum, item) => sum + item.price * item.quantity,
    0,
  );

  const handleCheckout = () => {
    const productLines = cartItems
      .map(
        (item) =>
          `${item.name}${item.quantity > 1 ? ` (x${item.quantity})` : ""}     ${formatPrice(item.price * item.quantity)}`
      )
      .join("\n");

    const message = `Hola, Oleaje!\n\nYa escogí mis productos, ahora quiero proceder con la compra!\n\nProductos:\n\n${productLines}\n\nValor total: ${formatPrice(total)}`;

    const encodedMessage = encodeURIComponent(message);
    const whatsappUrl = `https://wa.me/${config.whatsapp}?text=${encodedMessage}`;
    window.open(whatsappUrl, "_blank", "noopener,noreferrer");
  };

  return (
    <main className="page cart-summary-page">
      <div className="page-heading">
        <p className="eyebrow">Tu carrito</p>
        <h1>
          Resumen de <em>compra.</em>
        </h1>
        <p>Revisa tus piezas antes de iniciar el proceso de pago.</p>
      </div>
      {cartItems.length === 0 ? (
        <section className="empty-cart">
          <p>No hay productos en tu carrito todavía.</p>
          <button
            className="primary-button"
            onClick={() => setView("productos")}
          >
            Ver colección <span>→</span>
          </button>
        </section>
      ) : (
        <div className="cart-summary-grid">
          <section className="cart-table-section">
            <div className="cart-table-header">
              <span>Producto</span>
              <span>Precio</span>
              <span>Cantidad</span>
              <span>Subtotal</span>
              <span>Acción</span>
            </div>
            {cartItems.map((item) => (
              <div key={item.id} className="cart-table-row">
                <div className="cart-product-cell">
                  <img src={item.image} alt={item.name} />
                  <div>
                    <strong>{item.name}</strong>
                    <p>{item.category}</p>
                  </div>
                </div>
                <span>{formatPrice(item.price)}</span>
                <div className="cart-quantity-controls">
                  <button
                    type="button"
                    className="quantity-button"
                    onClick={() => decreaseQuantity(item.id)}
                    aria-label={`Disminuir cantidad de ${item.name}`}
                  >
                    −
                  </button>
                  <span>{item.quantity}</span>
                  <button
                    type="button"
                    className="quantity-button"
                    onClick={() => increaseQuantity(item.id)}
                    aria-label={`Aumentar cantidad de ${item.name}`}
                  >
                    +
                  </button>
                </div>
                <span>{formatPrice(item.price * item.quantity)}</span>
                <button
                  type="button"
                  className="cart-remove-button"
                  onClick={() => removeFromCart(item.id)}
                >
                  ×
                </button>
              </div>
            ))}
          </section>
          <aside className="checkout-panel">
            <div className="checkout-box">
              <div className="checkout-row">
                <span>Subtotal</span>
                <strong>{formatPrice(total)}</strong>
              </div>
              <div className="checkout-row total">
                <span>Total</span>
                <strong>{formatPrice(total)}</strong>
              </div>
            </div>
            <button
              className="primary-button"
              onClick={handleCheckout}
            >
              Continuar con la compra <span>→</span>
            </button>
          </aside>
        </div>
      )}
    </main>
  );
}

function Contact({ config }: { config: AppConfig }) {
  const whatsappHref = config.whatsapp ? `https://wa.me/${config.whatsapp}` : "#";
  const emailHref = config.email ? `mailto:${config.email}` : "#";
  // Formatea número para mostrar: 573014474936 → +57 301 447 4936
  const displayPhone = config.whatsapp
    ? `+${config.whatsapp.replace(/(\d{2})(\d{3})(\d{3})(\d{4})/, "$1 $2 $3 $4")}`
    : "";

  return (
    <main className="page contact-page">
      <div className="contact-hero">
        <p className="eyebrow light">Conversemos</p>
        <h1>
          Nos encanta
          <br />
          <em>escucharte.</em>
        </h1>
        <p>
          ¿Tienes una idea, pregunta o quieres una pieza especial? Escríbenos.
        </p>
      </div>
      <div className="contact-layout">
        <section className="contact-details">
          <p className="eyebrow">Estamos cerca</p>
          <h2>
            Hagamos algo
            <br />
            <em>bonito juntos.</em>
          </h2>
          <div className="detail-list">
            {config.email && (
              <div>
                <span>Escríbenos</span>
                <a href={emailHref}>{config.email}</a>
              </div>
            )}
            {config.whatsapp && (
              <div>
                <span>Llámanos o WhatsApp</span>
                <a href={whatsappHref} target="_blank" rel="noopener noreferrer">{displayPhone}</a>
              </div>
            )}
          </div>
          <div className="social-line">
            <a href="https://www.instagram.com/oleaje_col?igsh=Nnk1cHk3amo1ZTZ1&utm_source=qr" target="_blank" rel="noopener noreferrer">Instagram</a>
          </div>
        </section>
      </div>
    </main>
  );
}

function Admin({
  user,
  products,
  onLogout,
  onProductCreated,
  onProductDeleted,
  onProductUpdated,
}: {
  user: AdminUser;
  products: Product[];
  onLogout: () => void;
  onProductCreated: (product: Product) => void;
  onProductDeleted: (productId: number) => void;
  onProductUpdated: (product: Product) => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [name, setName] = useState("");
  const [category, setCategory] = useState<string>("");
  const [price, setPrice] = useState("");
  const [images, setImages] = useState<string[]>([]);
  const [stock, setStock] = useState("10");
  const [enDescuento, setEnDescuento] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const resetForm = () => {
    setName("");
    setCategory("Bolsos");
    setPrice("");
    setStock("10");
    setImages([]);
    setEnDescuento(false);
    setError("");
    setEditingProduct(null);
  };

  const editProduct = (product: Product) => {
    setEditingProduct(product);
    setName(product.name);
    setCategory(product.category);
    setPrice(String(product.price));
    setStock(String(product.stock ?? 10));
    setImages(product.images && product.images.length > 0 ? product.images : [product.image]);
    setEnDescuento(product.en_descuento);
    setError("");
    setShowForm(true);
  };

  const deleteProduct = async (id: number) => {
    if (!window.confirm("¿Estás seguro de que deseas eliminar este producto?")) {
      return;
    }
    try {
      const response = await fetch(`/api/products/${id}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (response.ok) {
        onProductDeleted(id);
      } else {
        const data = await response.json() as { message?: string };
        alert(data.message ?? "No fue posible eliminar el producto.");
      }
    } catch {
      alert("No fue posible conectar con el servicio.");
    }
  };

  const toggleDiscount = async (product: Product) => {
    const nextStatus = !product.en_descuento;
    try {
      const response = await fetch(`/api/products/${product.id}`, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ en_descuento: nextStatus }),
      });
      if (response.ok) {
        const data = (await response.json()) as { product: Product };
        onProductUpdated(data.product);
      } else {
        const data = await response.json() as { message?: string };
        alert(data.message ?? "No fue posible actualizar el descuento.");
      }
    } catch {
      alert("No fue posible conectar con el servicio.");
    }
  };

  const submitProduct = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      const url = editingProduct ? `/api/products/${editingProduct.id}` : "/api/products";
      const method = editingProduct ? "PATCH" : "POST";
      const response = await fetch(url, {
        method,
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          category,
          price: Number(price),
          stock: Number(stock),
          images,
          en_descuento: enDescuento,
        }),
      });
      const data = (await response.json()) as {
        message?: string;
        product?: Product;
      };
      if (!response.ok || !data.product) {
        setError(data.message ?? "No fue posible guardar el producto.");
        return;
      }
      if (editingProduct) {
        onProductUpdated(data.product);
      } else {
        onProductCreated(data.product);
      }
      resetForm();
      setShowForm(false);
    } catch {
      setError("No fue posible conectar con el servicio.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="admin-view">
      <aside className={`admin-sidebar ${sidebarOpen ? "open" : ""}`}>
        <button
          type="button"
          className="sidebar-close-btn"
          onClick={() => setSidebarOpen(false)}
          aria-label="Cerrar menú"
        >
          ×
        </button>
        <Brand inverse />
        <p className="admin-label">PANEL DE CONTROL</p>
        <button className="side-active">Productos</button>
        <button className="leave-admin" onClick={onLogout}>
          ← &nbsp; Cerrar sesión
        </button>
      </aside>

      {sidebarOpen && (
        <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} />
      )}

      <section className="admin-content">
        <button
          type="button"
          className="admin-menu-trigger"
          onClick={() => setSidebarOpen(true)}
        >
          ☰ Menú
        </button>
        <div className="admin-top">
          <div>
            <p className="eyebrow">Buenos días, {user.name}</p>
            <h1>
              Tu taller, en <em>orden.</em>
            </h1>
          </div>
          <button className="primary-button" onClick={() => { resetForm(); setShowForm(true); }}>
            + Nuevo producto
          </button>
        </div>
        <div className="stat-grid">
          <div>
            <span>Piezas publicadas</span>
            <b>{products.length}</b>
            <small>
              {products.length === 1
                ? "1 referencia activa"
                : `${products.length} referencias activas`}
            </small>
          </div>
        </div>
        <div className="table-card">
          <div className="table-head">
            <h2>Productos recientes</h2>
          </div>
          <div className="table-wrap">
            {products.length === 0 ? (
              <p className="admin-empty">Todavía no hay productos creados.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>PRODUCTO</th>
                    <th>CATEGORÍA</th>
                    <th>PRECIO</th>
                    <th>DISPONIBLES</th>
                    <th>DESCUENTO</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((product) => (
                    <tr key={product.id}>
                      <td>
                        <img src={product.image} alt="" />
                        {product.name}
                      </td>
                      <td data-label="Categoría">{product.category}</td>
                      <td data-label="Precio">{formatPrice(product.price)}</td>
                      <td data-label="Disponibles">{product.stock ?? 10} pcs</td>
                      <td data-label="Descuento">
                        <label className="switch-label">
                          <input
                            type="checkbox"
                            checked={product.en_descuento}
                            onChange={() => void toggleDiscount(product)}
                          />
                          <span className="switch-slider"></span>
                        </label>
                      </td>
                      <td data-label="Acciones" style={{ textAlign: "right" }}>
                        <div style={{ display: "inline-flex", gap: "8px", justifyContent: "flex-end" }}>
                          <button
                            type="button"
                            className="admin-edit-btn"
                            onClick={() => editProduct(product)}
                            aria-label={`Editar ${product.name}`}
                          >
                            Editar
                          </button>
                          <button
                            type="button"
                            className="admin-delete-btn"
                            onClick={() => void deleteProduct(product.id)}
                            aria-label={`Eliminar ${product.name}`}
                          >
                            Eliminar
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </section>
      {showForm && (
        <div className="modal-backdrop">
          <form className="product-form" onSubmit={submitProduct}>
            <button
              type="button"
              className="close-modal"
              onClick={() => {
                resetForm();
                setShowForm(false);
              }}
            >
              ×
            </button>
            <p className="eyebrow">{editingProduct ? "Modificar inventario" : "Nuevo inventario"}</p>
            <h2>{editingProduct ? "Editar producto" : "Crear producto"}</h2>
            <label>
              Nombre
              <input
                required
                placeholder="Nombre de la pieza"
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            <label>
              Imágenes del Producto
              <input
                type="file"
                accept="image/*"
                multiple
                onChange={async (event) => {
                  const files = Array.from(event.target.files || []);
                  if (files.length > 0) {
                    const uploadedUrls: string[] = [];
                    for (const file of files) {
                      const formData = new FormData();
                      formData.append("file", file);
                      try {
                        const res = await fetch("/api/upload", {
                          method: "POST",
                          credentials: "include",
                          body: formData,
                        });
                        if (res.ok) {
                          const data = (await res.json()) as { url?: string };
                          if (data.url) uploadedUrls.push(data.url);
                        }
                      } catch {
                        console.error("Error al subir imagen");
                      }
                    }
                    if (uploadedUrls.length > 0) {
                      setImages((prev) => [...prev, ...uploadedUrls]);
                    }
                  }
                }}
              />
              {images.length > 0 && (
                <div className="admin-image-previews">
                  {images.map((imgUrl, idx) => (
                    <div key={idx} className="admin-image-preview">
                      <img src={imgUrl} alt={`preview ${idx}`} />
                      <button
                        type="button"
                        onClick={() => setImages((prev) => prev.filter((_, i) => i !== idx))}
                        aria-label="Eliminar imagen"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </label>
            <div className="form-split">
              <label>
                Categoría
                <input
                  required
                  placeholder="Ej: Bolsos, Accesorios…"
                  value={category}
                  onChange={(event) => setCategory(event.target.value)}
                />
              </label>
              <label>
                Precio
                <input
                  type="number"
                  required
                  min="1"
                  placeholder="85000"
                  value={price}
                  onChange={(event) => setPrice(event.target.value)}
                />
              </label>
              <label>
                Piezas disponibles
                <input
                  type="number"
                  required
                  min="0"
                  placeholder="10"
                  value={stock}
                  onChange={(event) => setStock(event.target.value)}
                />
              </label>
            </div>
            <div className="form-checkbox-container">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={enDescuento}
                  onChange={(event) => setEnDescuento(event.target.checked)}
                />
                Marcar como producto en descuento
              </label>
            </div>
            {error && <p className="login-error" role="alert">{error}</p>}
            <button className="primary-button" type="submit" disabled={saving}>
              {saving ? "Guardando…" : (editingProduct ? "Guardar cambios →" : "Guardar producto →")}
            </button>
          </form>
        </div>
      )}
    </main>
  );
}

function DetailImageSlider({ product }: { product: Product }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const images = product.images && product.images.length > 0 ? product.images : [product.image];

  if (images.length <= 1) {
    return (
      <div className="detail-image-wrapper">
        <img src={images[0]} alt={product.name} />
      </div>
    );
  }

  const nextImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentIndex((prev) => (prev + 1) % images.length);
  };

  const prevImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentIndex((prev) => (prev - 1 + images.length) % images.length);
  };

  return (
    <div className="detail-image-wrapper">
      <img src={images[currentIndex]} alt={product.name} />

      {/* Invisible slider areas (click on left/right half of image) */}
      <div className="invisible-slider-areas">
        <div className="slider-area-left" onClick={prevImage} />
        <div className="slider-area-right" onClick={nextImage} />
      </div>

      {/* Visible slider arrows */}
      <div className="image-slider-controls">
        <button type="button" onClick={prevImage} aria-label="Imagen anterior">
          ‹
        </button>
        <button type="button" onClick={nextImage} aria-label="Siguiente imagen">
          ›
        </button>
      </div>

      {/* Visible slider dots */}
      <div className="image-slider-dots">
        {images.map((_, idx) => (
          <span
            key={idx}
            className={`slider-dot ${idx === currentIndex ? 'active' : ''}`}
            onClick={(e) => {
              e.stopPropagation();
              setCurrentIndex(idx);
            }}
          />
        ))}
      </div>
    </div>
  );
}

function App() {
  const config = useAppConfig();
  const [view, setView] = useState<View>("inicio");
  const [adminUser, setAdminUser] = useState<AdminUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [catalogProducts, setCatalogProducts] = useState<Product[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [selected, setSelected] = useState<Product | null>(null);
  const [notice, setNotice] = useState("");
  const [cartItems, setCartItems] = useState<CartItem[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const saved = window.localStorage.getItem("oleaje-cart");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const cartCount = cartItems.reduce((sum, item) => sum + item.quantity, 0);
  const addToBag = (product: Product) => {
    setCartItems((items) => {
      const existing = items.find((item) => item.id === product.id);
      if (existing) {
        return items.map((item) =>
          item.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item,
        );
      }
      return [...items, { ...product, quantity: 1 }];
    });
    setNotice(`${product.name} fue agregado a tu bolsa`);
    window.setTimeout(() => setNotice(""), 2800);
  };

  const removeFromCart = (productId: number) => {
    setCartItems((items) => items.filter((item) => item.id !== productId));
  };

  const changeQuantity = (productId: number, delta: number) => {
    setCartItems((items) =>
      items.flatMap((item) => {
        if (item.id !== productId) return item;
        const nextQuantity = item.quantity + delta;
        return nextQuantity > 0 ? [{ ...item, quantity: nextQuantity }] : [];
      }),
    );
  };

  const increaseQuantity = (productId: number) => changeQuantity(productId, 1);
  const decreaseQuantity = (productId: number) => changeQuantity(productId, -1);

  useEffect(() => {
    window.localStorage.setItem("oleaje-cart", JSON.stringify(cartItems));
  }, [cartItems]);

  const loadProducts = async () => {
    setCatalogLoading(true);
    try {
      const response = await fetch("/api/products");
      if (response.ok) {
        const data = (await response.json()) as { products?: Product[] };
        setCatalogProducts(data.products ?? []);
      }
    } catch {
      setCatalogProducts([]);
    } finally {
      setCatalogLoading(false);
    }
  };

  useEffect(() => {
    void loadProducts();
  }, []);

  useEffect(() => {
    const restoreSession = async () => {
      try {
        const response = await fetch("/api/auth/me", { credentials: "include" });
        if (response.ok) {
          const data = (await response.json()) as { user?: AdminUser };
          setAdminUser(data.user ?? null);
        } else {
          // 401 = no hay sesión activa, comportamiento esperado
          setAdminUser(null);
        }
      } catch {
        setAdminUser(null);
      } finally {
        setAuthChecked(true);
      }
    };
    void restoreSession();
  }, []);

  const logout = async () => {
    try {
      await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    } finally {
      setAdminUser(null);
      setView("inicio");
    }
  };

  const content =
    view === "inicio" ? (
      <Home setView={setView} />
    ) : view === "productos" ? (
      <Products
        products={catalogProducts}
        loading={catalogLoading}
        openProduct={setSelected}
        addToBag={addToBag}
      />
    ) : view === "carrito" ? (
      <CartSummary
        cartItems={cartItems}
        removeFromCart={removeFromCart}
        increaseQuantity={increaseQuantity}
        decreaseQuantity={decreaseQuantity}
        setView={setView}
        config={config}
      />
    ) : view === "contacto" ? (
      <Contact config={config} />
    ) : !authChecked ? (
      <main className="admin-login-page"><p>Comprobando sesión…</p></main>
    ) : adminUser ? (
      <Admin
        user={adminUser}
        products={catalogProducts}
        onLogout={() => void logout()}
        onProductCreated={(product) => {
          setCatalogProducts((items) => [product, ...items]);
          setNotice(`${product.name} fue publicado en la colección`);
          window.setTimeout(() => setNotice(""), 2800);
        }}
        onProductDeleted={(productId) => {
          setCatalogProducts((items) => items.filter((p) => p.id !== productId));
          setNotice("El producto fue eliminado de la colección");
          window.setTimeout(() => setNotice(""), 2800);
        }}
        onProductUpdated={(updatedProduct) => {
          setCatalogProducts((items) =>
            items.map((p) => (p.id === updatedProduct.id ? updatedProduct : p))
          );
        }}
      />
    ) : (
      <AdminLogin onSuccess={setAdminUser} onBack={() => setView("inicio")} />
    );
  return (
    <>
      {view !== "admin" && (
        <SiteHeader view={view} setView={setView} />
      )}
      {content}
      {view !== "admin" && <SiteFooter setView={setView} config={config} />}
      {view !== "admin" && view !== "carrito" && (
        <button
          className="floating-cart"
          onClick={() => setView("carrito")}
          aria-label="Abrir carrito"
        >
          <span className="cart-icon">🛒</span>
          <span className="cart-count">{cartCount}</span>
        </button>
      )}
      {notice && <div className="toast">✓ {notice}</div>}
      {selected && (
        <div className="modal-backdrop" onMouseDown={() => setSelected(null)}>
          <section
            className="detail-modal"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <button className="close-modal" onClick={() => setSelected(null)}>
              ×
            </button>
            <DetailImageSlider product={selected} />
            <div>
              <p className="eyebrow">
                {selected.category}
                {selected.en_descuento && (
                  <span className="discount-badge-modal">Descuento</span>
                )}
              </p>
              <h2>{selected.name}</h2>
              <strong>{formatPrice(selected.price)}</strong>
              <p>{selected.description}</p>
              <p className="detail-stock">
                ● {selected.stock} piezas disponibles
              </p>
              <button
                className="primary-button"
                onClick={() => {
                  addToBag(selected);
                  setSelected(null);
                }}
              >
                Añadir a mi bolsa <span>+</span>
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}

export default App;
