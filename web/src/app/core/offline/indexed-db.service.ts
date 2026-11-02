import { HttpClient } from '@angular/common/http';
import { DestroyRef, Injectable, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { API_URL } from '../api';

export interface DetalleSincronizacion {
  uuid_operacion: string;
  tipo: string;
  estado: string;
  venta_id?: number | null;
  nro_comprobante?: string | null;
  mensaje: string;
}

export interface SincronizacionLoteResultado {
  total_procesadas: number;
  confirmadas: number;
  rechazadas: number;
  conflictos: number;
  detalles: DetalleSincronizacion[];
}

export interface MetaOffline {
  clave: string;
  valor: any;
  fecha: string;
}

export interface ItemVentaOffline {
  variante_id: number;
  sku: string;
  prenda_nombre: string;
  talla: string;
  color: string;
  cantidad: number;
  precio_unitario: number;
  descuento: number;
  subtotal: number;
}

export interface VentaOffline {
  uuid_operacion: string;
  tipo: 'venta';
  sucursal_id: number;
  sucursal_nombre?: string | null;
  cajero_nombre?: string | null;
  cajero_id?: number | null;
  fecha_hora: string;
  total: number;
  subtotal: number;
  descuento: number;
  metodo_pago: 'efectivo';
  monto_recibido: number;
  cambio: number;
  items: ItemVentaOffline[];
  estado: 'LOCAL' | 'ENVIADA' | 'CONFIRMADA' | 'RECHAZADA' | 'EN_CONFLICTO';
  mensaje_servidor?: string | null;
  nro_comprobante?: string | null;
  fecha_sincronizacion?: string | null;
}

export interface DescargaOfflineRespuesta {
  version: number;
  fecha_sincronizacion: string;
  sucursal_id: number | null;
  sucursal_nombre: string | null;
  total_prendas: number;
  prendas: any[];
  categorias: any[];
}

const DB_NOMBRE = 'gangaclothes_offline';
const DB_VERSION = 1;

export const STORES = {
  CATALOGO: 'catalogo_local',
  META: 'meta_offline',
  OPERACIONES: 'operaciones_pendientes',
} as const;

/**
 * Servicio centralizado de IndexedDB para la PWA de GangaClothes.
 * Soporta CU-11 (Descarga), CU-12 (Consulta Offline), CU-13 y CU-14 (Operaciones Offline).
 */
@Injectable({ providedIn: 'root' })
export class IndexedDbService {
  private http = inject(HttpClient);
  private dbPromise: Promise<IDBDatabase> | null = null;

  /** Estado de conectividad de red del navegador */
  readonly online = signal<boolean>(typeof navigator !== 'undefined' ? navigator.onLine : true);

  /** Información de la última descarga local */
  readonly fechaUltimaDescarga = signal<string | null>(null);
  readonly prendasEnCache = signal<number>(0);
  readonly descargando = signal<boolean>(false);

  /** Cantidad de operaciones (ventas / reservas) pendientes de sincronización (CU-15) */
  readonly operacionesPendientesCount = signal<number>(0);

  constructor() {
    if (typeof window !== 'undefined') {
      const onOnline = () => {
        this.online.set(true);
        this.autoSincronizar();
      };
      const onOffline = () => this.online.set(false);

      window.addEventListener('online', onOnline);
      window.addEventListener('offline', onOffline);

      inject(DestroyRef).onDestroy(() => {
        window.removeEventListener('online', onOnline);
        window.removeEventListener('offline', onOffline);
      });

      // Inicializar y cargar metadata en segundo plano
      this.cargarMetadataLocal();
    }
  }

  // ---------------------------------------------------------------- Conexión
  private obtenerDB(): Promise<IDBDatabase> {
    if (this.dbPromise) return this.dbPromise;

    this.dbPromise = new Promise((resolve, reject) => {
      if (typeof window === 'undefined' || !window.indexedDB) {
        reject(new Error('IndexedDB no está disponible en este entorno.'));
        return;
      }

      const peticion = window.indexedDB.open(DB_NOMBRE, DB_VERSION);

      peticion.onupgradeneeded = (evento: IDBVersionChangeEvent) => {
        const db = (evento.target as IDBOpenDBRequest).result;

        // 1. Almacén de catálogo de productos
        if (!db.objectStoreNames.contains(STORES.CATALOGO)) {
          const storeCatalogo = db.createObjectStore(STORES.CATALOGO, { keyPath: 'id' });
          storeCatalogo.createIndex('categoria_id', 'categoria_id', { unique: false });
          storeCatalogo.createIndex('nombre', 'nombre', { unique: false });
        }

        // 2. Almacén de metadatos (fecha de sincronización, sucursal, etc.)
        if (!db.objectStoreNames.contains(STORES.META)) {
          db.createObjectStore(STORES.META, { keyPath: 'clave' });
        }

        // 3. Almacén de operaciones pendientes generadas offline (ventas, reservas)
        if (!db.objectStoreNames.contains(STORES.OPERACIONES)) {
          const storeOps = db.createObjectStore(STORES.OPERACIONES, { keyPath: 'uuid_operacion' });
          storeOps.createIndex('tipo', 'tipo', { unique: false });
          storeOps.createIndex('estado', 'estado', { unique: false });
          storeOps.createIndex('fecha_creacion', 'fecha_creacion', { unique: false });
        }
      };

      peticion.onsuccess = () => resolve(peticion.result);
      peticion.onerror = () => reject(peticion.error);
    });

    return this.dbPromise;
  }

  // ---------------------------------------------------------------- CU-11: Descarga
  /**
   * Solicita el dataset de catálogo al servidor y lo almacena localmente en IndexedDB.
   */
  descargarCatalogo(sucursalId?: number | null): Observable<DescargaOfflineRespuesta> {
    this.descargando.set(true);
    let url = `${API_URL}/catalogo/descarga-offline`;
    if (sucursalId) url += `?sucursal_id=${sucursalId}`;

    return this.http.get<DescargaOfflineRespuesta>(url).pipe(
      tap({
        next: async (respuesta) => {
          await this.guardarEnIndexedDB(respuesta);
          this.fechaUltimaDescarga.set(respuesta.fecha_sincronizacion);
          this.prendasEnCache.set(respuesta.total_prendas);
          this.descargando.set(false);
        },
        error: () => {
          this.descargando.set(false);
        },
      }),
    );
  }

  private async guardarEnIndexedDB(datos: DescargaOfflineRespuesta): Promise<void> {
    const db = await this.obtenerDB();
    return new Promise((resolve, reject) => {
      const transaccion = db.transaction([STORES.CATALOGO, STORES.META], 'readwrite');
      const storeCatalogo = transaccion.objectStore(STORES.CATALOGO);
      const storeMeta = transaccion.objectStore(STORES.META);

      // Limpiar catálogo anterior e insertar el nuevo
      storeCatalogo.clear();
      for (const prenda of datos.prendas) {
        storeCatalogo.put(prenda);
      }

      // Guardar metadatos de sincronización
      storeMeta.put({
        clave: 'sincronizacion_catalogo',
        valor: {
          fecha: datos.fecha_sincronizacion,
          sucursal_id: datos.sucursal_id,
          sucursal_nombre: datos.sucursal_nombre,
          total: datos.total_prendas,
        },
        fecha: datos.fecha_sincronizacion,
      });

      transaccion.oncomplete = () => resolve();
      transaccion.onerror = () => reject(transaccion.error);
    });
  }

  /**
   * Auto-sincronización transparente en segundo plano (Background Caching):
   * Guarda las prendas automáticamente sin que el usuario tenga que apretar ningún botón.
   */
  async autoGuardarEnSegundoPlano(prendas: any[], sucursalId?: number | null): Promise<void> {
    if (!prendas || prendas.length === 0) return;
    try {
      const db = await this.obtenerDB();
      const ahora = new Date().toISOString();
      const tx = db.transaction([STORES.CATALOGO, STORES.META], 'readwrite');
      const storeCatalogo = tx.objectStore(STORES.CATALOGO);
      const storeMeta = tx.objectStore(STORES.META);

      storeCatalogo.clear();
      for (const p of prendas) {
        storeCatalogo.put(p);
      }

      storeMeta.put({
        clave: 'sincronizacion_catalogo',
        valor: {
          fecha: ahora,
          sucursal_id: sucursalId,
          total: prendas.length,
          metodo: 'automatico',
        },
        fecha: ahora,
      });

      this.fechaUltimaDescarga.set(ahora);
      this.prendasEnCache.set(prendas.length);
    } catch {
      // Silencioso: no interrumpe la navegación
    }
  }

  // ---------------------------------------------------------------- CU-12: Consulta Local
  /**
   * Consulta las prendas almacenadas localmente en IndexedDB.
   */
  async obtenerCatalogoLocal(filtro?: { categoriaId?: number | null; q?: string }): Promise<any[]> {
    const db = await this.obtenerDB();
    return new Promise((resolve, reject) => {
      const transaccion = db.transaction(STORES.CATALOGO, 'readonly');
      const store = transaccion.objectStore(STORES.CATALOGO);
      const peticion = store.getAll();

      peticion.onsuccess = () => {
        let resultados: any[] = peticion.result || [];

        if (filtro?.categoriaId) {
          resultados = resultados.filter((p) => p.categoria_id === filtro.categoriaId);
        }

        if (filtro?.q) {
          const texto = filtro.q.trim().toLowerCase();
          resultados = resultados.filter(
            (p) =>
              (p.nombre && p.nombre.toLowerCase().includes(texto)) ||
              (p.marca && p.marca.toLowerCase().includes(texto)) ||
              (p.descripcion && p.descripcion.toLowerCase().includes(texto)),
          );
        }

        resolve(resultados);
      };

      peticion.onerror = () => reject(peticion.error);
    });
  }

  async cargarMetadataLocal(): Promise<void> {
    try {
      const db = await this.obtenerDB();
      const meta = await new Promise<MetaOffline | null>((resolve) => {
        const tx = db.transaction(STORES.META, 'readonly');
        const req = tx.objectStore(STORES.META).get('sincronizacion_catalogo');
        req.onsuccess = () => resolve(req.result ?? null);
        req.onerror = () => resolve(null);
      });

      if (meta && meta.valor) {
        this.fechaUltimaDescarga.set(meta.valor.fecha);
        this.prendasEnCache.set(meta.valor.total || 0);
      }

      await this.actualizarContadorPendientes();
    } catch {
      // Entornos sin IndexedDB o primer inicio
    }
  }

  // ---------------------------------------------------------------- CU-14: Operación de Venta Offline
  /**
   * Guarda una venta procesada sin conexión en IndexedDB y decrementa el stock local inmediatamente.
   */
  async guardarVentaOffline(venta: VentaOffline): Promise<void> {
    const db = await this.obtenerDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction([STORES.OPERACIONES, STORES.CATALOGO], 'readwrite');
      const storeOps = tx.objectStore(STORES.OPERACIONES);
      const storeCatalogo = tx.objectStore(STORES.CATALOGO);

      // 1. Guardar la venta en la bandeja local
      storeOps.put(venta);

      // 2. Decrementar el stock local de cada variante vendida
      for (const item of venta.items) {
        const req = storeCatalogo.openCursor();
        req.onsuccess = (e) => {
          const cursor = (e.target as IDBRequest<IDBCursorWithValue>).result;
          if (cursor) {
            const prenda = cursor.value;
            let modificada = false;

            if (prenda.variantes && Array.isArray(prenda.variantes)) {
              for (const v of prenda.variantes) {
                if (v.id === item.variante_id) {
                  // Decrementar existencias
                  if (typeof v.disponible === 'number') {
                    v.disponible = Math.max(0, v.disponible - item.cantidad);
                  }
                  if (v.disponibilidad && Array.isArray(v.disponibilidad)) {
                    for (const d of v.disponibilidad) {
                      if (d.sucursal_id === venta.sucursal_id) {
                        d.disponible = Math.max(0, d.disponible - item.cantidad);
                      }
                    }
                  }
                  modificada = true;
                }
              }
            }

            if (modificada) {
              cursor.update(prenda);
            } else {
              cursor.continue();
            }
          }
        };
      }

      tx.oncomplete = () => {
        this.actualizarContadorPendientes();
        resolve();
      };
      tx.onerror = () => reject(tx.error);
    });
  }

  async obtenerOperacionesPendientes(): Promise<VentaOffline[]> {
    const db = await this.obtenerDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.OPERACIONES, 'readonly');
      const store = tx.objectStore(STORES.OPERACIONES);
      const req = store.getAll();
      req.onsuccess = () => {
        const todas: VentaOffline[] = req.result || [];
        resolve(todas.filter((op) => op.estado === 'LOCAL'));
      };
      req.onerror = () => reject(req.error);
    });
  }

  async obtenerTodasOperaciones(): Promise<VentaOffline[]> {
    const db = await this.obtenerDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.OPERACIONES, 'readonly');
      const store = tx.objectStore(STORES.OPERACIONES);
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  }

  async actualizarContadorPendientes(): Promise<number> {
    try {
      const pendientes = await this.obtenerOperacionesPendientes();
      this.operacionesPendientesCount.set(pendientes.length);
      return pendientes.length;
    } catch {
      return 0;
    }
  }

  // ---------------------------------------------------------------- CU-16 y CU-17: Sincronización en Lote
  /**
   * Envía las operaciones locales con estado 'LOCAL' al backend central.
   */
  async sincronizarLote(): Promise<SincronizacionLoteResultado | null> {
    const pendientes = await this.obtenerOperacionesPendientes();
    if (!pendientes || pendientes.length === 0) return null;

    // Agrupar por sucursal_id
    const porSucursal = new Map<number, VentaOffline[]>();
    for (const p of pendientes) {
      const lista = porSucursal.get(p.sucursal_id) || [];
      lista.push(p);
      porSucursal.set(p.sucursal_id, lista);
    }

    let resultadoGlobal: SincronizacionLoteResultado = {
      total_procesadas: 0,
      confirmadas: 0,
      rechazadas: 0,
      conflictos: 0,
      detalles: [],
    };

    for (const [sucursalId, operaciones] of porSucursal.entries()) {
      const payload = {
        sucursal_id: sucursalId,
        operaciones: operaciones.map((op) => ({
          uuid_operacion: op.uuid_operacion,
          tipo: op.tipo,
          fecha_hora: op.fecha_hora,
          total: op.total,
          subtotal: op.subtotal,
          descuento: op.descuento,
          metodo_pago: op.metodo_pago,
          monto_recibido: op.monto_recibido,
          items: op.items.map((it) => ({
            variante_id: it.variante_id,
            cantidad: it.cantidad,
            precio_unitario: it.precio_unitario,
          })),
        })),
      };

      try {
        const respuesta = await new Promise<SincronizacionLoteResultado>((resolve, reject) => {
          this.http.post<SincronizacionLoteResultado>(`${API_URL}/sincronizacion/lote`, payload).subscribe({
            next: (res) => resolve(res),
            error: (err) => reject(err),
          });
        });

        // Actualizar el estado de cada operación en IndexedDB según la respuesta del servidor
        await this.actualizarEstadosLocales(respuesta.detalles);

        resultadoGlobal.total_procesadas += respuesta.total_procesadas;
        resultadoGlobal.confirmadas += respuesta.confirmadas;
        resultadoGlobal.rechazadas += respuesta.rechazadas;
        resultadoGlobal.conflictos += respuesta.conflictos;
        resultadoGlobal.detalles.push(...respuesta.detalles);
      } catch (err) {
        // Error de red durante la sincronización
      }
    }

    await this.actualizarContadorPendientes();
    return resultadoGlobal;
  }

  private async actualizarEstadosLocales(detalles: DetalleSincronizacion[]): Promise<void> {
    const db = await this.obtenerDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.OPERACIONES, 'readwrite');
      const store = tx.objectStore(STORES.OPERACIONES);

      for (const d of detalles) {
        const req = store.get(d.uuid_operacion);
        req.onsuccess = () => {
          const op: VentaOffline = req.result;
          if (op) {
            op.estado = d.estado as any;
            (op as any).mensaje_servidor = d.mensaje;
            (op as any).nro_comprobante = d.nro_comprobante;
            (op as any).fecha_sincronizacion = new Date().toISOString();
            store.put(op);
          }
        };
      }

      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  async autoSincronizar(): Promise<void> {
    if (this.operacionesPendientesCount() > 0) {
      await this.sincronizarLote();
    }
  }

  async limpiarCatalogoLocal(): Promise<void> {
    const db = await this.obtenerDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction([STORES.CATALOGO, STORES.META], 'readwrite');
      tx.objectStore(STORES.CATALOGO).clear();
      tx.objectStore(STORES.META).delete('sincronizacion_catalogo');
      tx.oncomplete = () => {
        this.fechaUltimaDescarga.set(null);
        this.prendasEnCache.set(0);
        resolve();
      };
      tx.onerror = () => reject(tx.error);
    });
  }
}
