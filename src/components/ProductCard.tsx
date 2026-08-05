import { useState } from "react";
import type { Product } from "../types";
import { formatPrice } from "../data/products";

interface Props {
  product: Product;
  onDetail: (product: Product) => void;
  onBuy: (product: Product) => void;
}

export function ProductCard({ product, onDetail, onBuy }: Props) {
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
        {product.en_descuento && (
          <span className="discount-tag-card">Descuento</span>
        )}
      </div>
      <div className="product-copy">
        <h3>{product.name}</h3>
        <p>{product.description}</p>
        <div className="product-bottom">
          <strong>{formatPrice(product.price)}</strong>
          <button className="text-button" onClick={() => onDetail(product)}>
            Ver detalle <b>→</b>
          </button>
        </div>
        <button className="buy-button" onClick={() => onBuy(product)}>
          Añadir a mi bolsa <span>+</span>
        </button>
      </div>
    </article>
  );
}
