export type Category = string

export interface Product {
  id: number
  name: string
  category: string
  price: number
  description: string
  image: string
  images: string[]
  featured?: boolean
  stock: number
  en_descuento: boolean
  descuento_fin?: string | null
  sizes?: Record<string, number> | null
}

export type View = 'inicio' | 'productos' | 'carrito' | 'contacto' | 'admin'
