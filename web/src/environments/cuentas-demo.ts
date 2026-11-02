/**
 * Atajos de login para la demostracion en clase (usuarios de backend/seed.py).
 * En la compilacion de produccion este archivo se reemplaza por
 * `cuentas-demo.prod.ts`, que devuelve una lista vacia: asi las credenciales
 * no viajan dentro del bundle publicado en Vercel.
 */
export interface CuentaDemo {
  rol: string;
  email: string;
  password: string;
  codigo_tenant?: string;
}

export const CUENTAS_DEMO: CuentaDemo[] = [
  { rol: 'admin (GangaClothes)', email: 'admin@gangaclothes.com', password: 'Admin123!', codigo_tenant: 'gangaclothes' },
  { rol: 'admin (Boutique Luna)', email: 'admin@luna.com', password: 'Luna123!', codigo_tenant: 'luna' },
  { rol: 'encargado', email: 'encargado@gangaclothes.com', password: 'Encargado123!', codigo_tenant: 'gangaclothes' },
  { rol: 'cajero', email: 'cajero@gangaclothes.com', password: 'Cajero123!', codigo_tenant: 'gangaclothes' },
  { rol: 'superadmin', email: 'superadmin@fashionstore.com', password: 'SuperAdmin123!' },
  { rol: 'cliente', email: 'sofia@gangaclothes.com', password: 'Cliente#2026' },
  { rol: 'proveedor', email: 'proveedor@gangaclothes.com', password: 'Proveedor123!' },
];
