/** Version de produccion: sin credenciales. Ver `cuentas-demo.ts`. */
export interface CuentaDemo {
  rol: string;
  email: string;
  password: string;
  codigo_tenant?: string;
}

export const CUENTAS_DEMO: CuentaDemo[] = [];
