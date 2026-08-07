export const formatPrice = (price: number) =>
  new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(price)

import type { Product } from "../types";

export const isDiscountValid = (product: Product): boolean => {
  if (!product.en_descuento) return false;
  if (!product.descuento_fin) return true;
  return new Date(product.descuento_fin) > new Date();
};
