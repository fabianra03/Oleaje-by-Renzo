import { useState } from "react";
import type { Product } from "../types";
import { formatPrice, isDiscountValid } from "../data/products";

interface Props {
  product: Product;
  onDetail: (product: Product) => void;
  onBuy: (product: Product) => void;
}

export function ProductCard({ product, onDetail }: Props) {
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const images = product.images && product.images.length > 0 ? product.images : [product.image];

  const nextImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentImageIndex((prev) => (prev + 1) % images.length);
  };

  const prevImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentImageIndex((prev) => (prev - 1 + images.length) % images.length);
  };

  return (
    <article className="product-card">
      <div
        className="product-image"
        onClick={() => onDetail(product)}
        style={{ cursor: "pointer" }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            onDetail(product);
          }
        }}
        aria-label={`Ver ${product.name}`}
      >
        <img src={images[currentImageIndex]} alt={product.name} />
        {images.length > 1 && (
          <>
            {/* Invisible slider click zones */}
            <div className="invisible-slider-areas">
              <div className="slider-area-left" onClick={prevImage} />
              <div className="slider-area-right" onClick={nextImage} />
            </div>

            {/* Visible slider controls */}
            <div className="image-slider-controls">
              <button type="button" onClick={prevImage} aria-label="Imagen anterior">
                ‹
              </button>
              <button type="button" onClick={nextImage} aria-label="Siguiente imagen">
                ›
              </button>
            </div>

            {/* Visible pagination dots */}
            <div className="image-slider-dots">
              {images.map((_, idx) => (
                <span
                  key={idx}
                  className={`slider-dot ${idx === currentImageIndex ? "active" : ""}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    setCurrentImageIndex(idx);
                  }}
                />
              ))}
            </div>
          </>
        )}
        <span className="category-tag">{product.category}</span>
        {isDiscountValid(product) && (
          <span className="discount-tag-card">Descuento</span>
        )}
      </div>
      <div className="product-copy">
        <h3>{product.name}</h3>
        <p>{product.description}</p>
        <div className="product-bottom">
          <strong>{(() => {
            if (product.sizes && Object.keys(product.sizes).length > 0) {
              const prices = Object.values(product.sizes);
              const min = Math.min(...prices);
              const max = Math.max(...prices);
              if (min === max) return formatPrice(min);
              return `${formatPrice(min)} – ${formatPrice(max)}`;
            }
            return formatPrice(product.price);
          })()}</strong>
          <button className="text-button" onClick={() => onDetail(product)}>
            Ver detalle <b>→</b>
          </button>
        </div>
        {product.sizes && Object.keys(product.sizes).length > 0 && (
          <div className="product-sizes-preview">
            {Object.keys(product.sizes).map((sz) => (
              <span key={sz} className="size-pill-preview">{sz}</span>
            ))}
          </div>
        )}
        <button className="buy-button" onClick={() => onDetail(product)}>
          {product.sizes && Object.keys(product.sizes).length > 0
            ? <>Seleccionar talla <span>→</span></>
            : <>Añadir a mi bolsa <span>+</span></>
          }
        </button>
      </div>
    </article>
  );
}
