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
}

export type View = 'inicio' | 'productos' | 'carrito' | 'contacto' | 'admin'
