import { CommonModule, DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { API_URL } from '../../../core/api';
import { Notificaciones } from '../../../core/notificaciones';
import { SesionStore } from '../../../core/sesion';
import { SucursalActual } from '../../../core/sucursal-actual';
import { moneda } from '../../../shared/formato';

export interface ItemVentaDevolucion {
  detalle_id: number;
  variante_id: number;
  sku: string;
  prenda: string;
  talla: string;
  color: string;
  precio_unitario: number;
  cantidad_comprada: number;
  cantidad_devuelta_previa: number;
  cantidad_disponible_devolucion: number;
  habilitado: boolean;
  // Campos de formulario en pantalla
  seleccionado?: boolean;
  cantidad_a_devolver?: number;
}

export interface VentaParaDevolucion {
  venta_id: number;
  nro_comprobante: string;
  fecha_venta: string;
  total_venta: number;
  estado: string;
  sucursal: string;
  sucursal_id: number;
  cajero: string;
  dias_transcurridos: number;
  dias_maximos_garantia: number;
  dias_restantes: number;
  plazo_vigente: boolean;
  mensaje_garantia: string;
  total_unidades_devolvibles: number;
  items: ItemVentaDevolucion[];
}

export interface DevolucionRegistrada {
  devolucion_id: number;
  nro_comprobante: string;
  venta_id: number;
  nro_comprobante_venta: string;
  fecha: string;
  sucursal: string;
  cajero: string;
  motivo: string;
  metodo_reembolso: string;
  total_devuelto: number;
  items: Array<{
    variante_id: number;
    sku: string;
    prenda: string;
    cantidad: number;
    precio_unitario: number;
    subtotal: number;
  }>;
}

@Component({
  selector: 'app-devoluciones',
  standalone: true,
  imports: [CommonModule, FormsModule, DatePipe],
  template: `
    <div class="cabecera-seccion">
      <div>
        <span class="ceja">Hito 4 · Postventa & Operaciones de Caja</span>
        <h1>Devoluciones de Prendas de Vestir (CU-23)</h1>
        <p class="subtitulo">
          Búsqueda de ventas, validación estricta de plazo comercial (30 días), restitución atómica al stock físico y emisión de comprobante de egreso.
        </p>
      </div>

      <div class="botones-pestana">
        <button
          type="button"
          class="btn"
          [class.rosa]="vistaActiva() === 'procesar'"
          [class.linea]="vistaActiva() !== 'procesar'"
          (click)="vistaActiva.set('procesar')"
        >
          Nueva Devolución
        </button>
        <button
          type="button"
          class="btn"
          [class.rosa]="vistaActiva() === 'historial'"
          [class.linea]="vistaActiva() !== 'historial'"
          (click)="cambiarAHistorial()"
        >
          Historial de Devoluciones
        </button>
      </div>
    </div>

    @if (vistaActiva() === 'procesar') {
      <!-- 1. BUSCADOR DE COMPROBANTE ORIGINAL -->
      <div class="bloque-busqueda">
        <label class="etiqueta" for="input-comp">Buscar Venta Original</label>
        <div class="fila-busqueda">
          <input
            id="input-comp"
            type="text"
            class="campo input-grande"
            placeholder="Introduce el N° de Comprobante (ej. B001-00001) o ID de la compra..."
            [(ngModel)]="terminoBusqueda"
            (keydown.enter)="buscarVenta()"
          />
          <button
            type="button"
            class="btn rosa"
            (click)="buscarVenta()"
            [disabled]="buscando() || !terminoBusqueda.trim()"
          >
            {{ buscando() ? 'Buscando...' : '🔍 Buscar Venta' }}
          </button>
        </div>
      </div>

      @if (errorBusqueda()) {
        <div class="mensaje error">{{ errorBusqueda() }}</div>
      }

      <!-- 2. DETALLE DE LA VENTA ENCONTRADA -->
      @if (venta(); as v) {
        <div class="bloque-venta-encontrada">
          <!-- Cabecera y Garantía -->
          <div class="resumen-venta-top">
            <div>
              <h2>Comprobante: {{ v.nro_comprobante }}</h2>
              <span class="meta-txt">
                Fecha: {{ v.fecha_venta | date: 'dd/MM/yyyy HH:mm' }} · Sucursal: <b>{{ v.sucursal }}</b> · Atendido por: {{ v.cajero }}
              </span>
            </div>

            <div class="badge-garantia" [class.vigente]="v.plazo_vigente" [class.expirada]="!v.plazo_vigente">
              <span class="icono-garantia">{{ v.plazo_vigente ? '🛡️' : '⚠️' }}</span>
              <div>
                <b>{{ v.plazo_vigente ? 'Garantía Vigente' : 'Plazo Expirado' }}</b>
                <small>{{ v.mensaje_garantia }}</small>
              </div>
            </div>
          </div>

          <!-- Tabla de prendas para seleccionar devolución -->
          <div class="marco-tabla">
            <table>
              <thead>
                <tr>
                  <th style="width: 40px;"></th>
                  <th>SKU / Prenda</th>
                  <th>Talla / Color</th>
                  <th>Precio Cobrado</th>
                  <th>Compradas</th>
                  <th>Ya Devueltas</th>
                  <th>Disponible a Devolver</th>
                  <th>Cant. a Devolver</th>
                  <th>Subtotal Reembolso</th>
                </tr>
              </thead>
              <tbody>
                @for (item of v.items; track item.detalle_id) {
                  <tr [class.inhabilitada]="!item.habilitado">
                    <td style="text-align: center;">
                      <input
                        type="checkbox"
                        [(ngModel)]="item.seleccionado"
                        [disabled]="!item.habilitado"
                        (change)="calcularTotal()"
                      />
                    </td>
                    <td>
                      <b>{{ item.prenda }}</b>
                      <small class="sku-sub">{{ item.sku }}</small>
                    </td>
                    <td>{{ item.talla }} / {{ item.color }}</td>
                    <td>Bs {{ moneda(item.precio_unitario) }}</td>
                    <td>{{ item.cantidad_comprada }} u.</td>
                    <td>{{ item.cantidad_devuelta_previa }} u.</td>
                    <td>
                      <b [class.sin-cupo]="item.cantidad_disponible_devolucion === 0">
                        {{ item.cantidad_disponible_devolucion }} u.
                      </b>
                    </td>
                    <td>
                      <input
                        type="number"
                        class="campo cant-input"
                        min="1"
                        [max]="item.cantidad_disponible_devolucion"
                        [(ngModel)]="item.cantidad_a_devolver"
                        [disabled]="!item.seleccionado"
                        (input)="validarCantidad(item)"
                      />
                    </td>
                    <td>
                      <b>Bs {{ moneda((item.cantidad_a_devolver || 0) * item.precio_unitario) }}</b>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>

          <!-- Formulario de confirmación y motivo -->
          <div class="panel-confirmacion">
            <div class="campos-motivo">
              <div>
                <label class="etiqueta" for="motivo-dev">Motivo de la Devolución <b class="req">*</b></label>
                <input
                  id="motivo-dev"
                  type="text"
                  class="campo"
                  placeholder="Ej: Talla incorrecta, cliente solicita cambio/reembolso..."
                  [(ngModel)]="motivo"
                />
              </div>

              <div>
                <label class="etiqueta" for="metodo-reemb">Método de Reembolso</label>
                <select id="metodo-reemb" class="campo" [(ngModel)]="metodoReembolso">
                  <option value="efectivo">Efectivo en Caja</option>
                  <option value="nota_credito">Nota de Crédito</option>
                </select>
              </div>
            </div>

            <div class="resumen-reembolso">
              <span class="label-reembolso">Total a Reembolsar:</span>
              <span class="monto-reembolso">Bs {{ moneda(totalReembolso()) }}</span>

              <button
                type="button"
                class="btn rosa btn-confirmar"
                (click)="confirmarDevolucion()"
                [disabled]="procesando() || totalReembolso() === 0 || !motivo.trim() || !v.plazo_vigente"
              >
                {{ procesando() ? 'Procesando Reingreso...' : '🔄 Confirmar Devolución (CU-23)' }}
              </button>
            </div>
          </div>
        </div>
      }
    } @else {
      <!-- HISTORIAL DE DEVOLUCIONES -->
      <div class="bloque-historial">
        @if (cargandoHistorial()) {
          <div class="mensaje">Cargando historial de devoluciones...</div>
        } @else if (historial().length === 0) {
          <div class="mensaje vacio">No hay devoluciones registradas en esta sucursal.</div>
        } @else {
          <div class="marco-tabla">
            <table>
              <thead>
                <tr>
                  <th>N° Comprobante Dev.</th>
                  <th>Venta Original</th>
                  <th>Fecha y Hora</th>
                  <th>Sucursal</th>
                  <th>Atendido por</th>
                  <th>Motivo</th>
                  <th>Método</th>
                  <th>Total Reembolsado</th>
                </tr>
              </thead>
              <tbody>
                @for (d of historial(); track d.id) {
                  <tr>
                    <td><b class="dev-comp">{{ d.nro_comprobante }}</b></td>
                    <td><span>{{ d.nro_comprobante_venta }}</span></td>
                    <td>{{ d.fecha | date: 'dd/MM/yyyy HH:mm' }}</td>
                    <td>{{ d.sucursal }}</td>
                    <td>{{ d.cajero }}</td>
                    <td>{{ d.motivo }}</td>
                    <td><span class="tag-metodo">{{ d.metodo_reembolso }}</span></td>
                    <td><b>Bs {{ moneda(d.total_devuelto) }}</b></td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </div>
    }

    <!-- MODAL DE COMPROBANTE DE DEVOLUCIÓN CONFIRMADA -->
    @if (devolucionEmitida(); as dev) {
      <div class="fondo" (click)="cerrarModalComprobante()">
        <div class="modal modal-devolucion" (click)="$event.stopPropagation()">
          <div class="ticket-dev">
            <div class="centro espaciado">GANGACLOTHES</div>
            <div class="centro pequeno">{{ dev.sucursal }} · Comprobante de Devolución</div>

            <div class="folio-dev">
              <span>COMPROBANTE N°</span>
              <b>{{ dev.nro_comprobante }}</b>
            </div>

            <div class="meta-ticket">
              <div>Venta Original: <b>{{ dev.nro_comprobante_venta }}</b></div>
              <div>Fecha: {{ dev.fecha | date: 'dd/MM/yyyy HH:mm:ss' }}</div>
              <div>Cajero: {{ dev.cajero }}</div>
              <div>Motivo: {{ dev.motivo }}</div>
            </div>

            <div class="items-dev-lista">
              @for (it of dev.items; track it.variante_id) {
                <div class="fila-dev-item">
                  <span>{{ it.cantidad }}× {{ it.prenda }} ({{ it.sku }})</span>
                  <span>Bs {{ moneda(it.subtotal) }}</span>
                </div>
              }
            </div>

            <div class="total-dev-fila">
              <span>TOTAL REEMBOLSADO</span>
              <b>Bs {{ moneda(dev.total_devuelto) }}</b>
            </div>

            <div class="reembolso-tipo">
              Forma de reintegro: <b>{{ dev.metodo_reembolso | uppercase }}</b>
            </div>

            <div class="aviso-stock-reintegrado">
              ✓ Stock reintegrado automáticamente al inventario físico y asentado en Kardex.
            </div>
          </div>

          <div class="acciones">
            <button type="button" class="btn linea" (click)="cerrarModalComprobante()">Cerrar</button>
            <button type="button" class="btn rosa" (click)="imprimirTicket()">🖨️ Imprimir Comprobante</button>
          </div>
        </div>
      </div>
    }
  `,
  styles: `
    .cabecera-seccion {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 22px;
      gap: 16px;
      flex-wrap: wrap;
    }
    h1 {
      font-size: 24px;
      font-weight: 800;
      color: var(--tinta);
      letter-spacing: -0.02em;
      margin: 4px 0 6px;
    }
    .subtitulo {
      font-size: 13.5px;
      color: var(--gris);
      max-width: 720px;
      line-height: 1.5;
    }
    .botones-pestana {
      display: flex;
      gap: 8px;
    }
    .bloque-busqueda {
      background: #ffffff;
      border: 1px solid var(--linea);
      border-radius: 14px;
      padding: 20px 24px;
      margin-bottom: 22px;
      box-shadow: var(--sombra-sm);
    }
    .fila-busqueda {
      display: flex;
      gap: 10px;
      align-items: center;
      margin-top: 6px;
    }
    .input-grande {
      flex: 1;
      font-size: 14px;
      padding: 10px 14px;
    }
    .bloque-venta-encontrada {
      background: #ffffff;
      border: 1px solid var(--linea);
      border-radius: 16px;
      padding: 24px 28px;
      box-shadow: var(--sombra-sm);
      margin-bottom: 26px;
    }
    .resumen-venta-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 20px;
      gap: 16px;
      flex-wrap: wrap;
    }
    .resumen-venta-top h2 {
      font-size: 19px;
      font-weight: 800;
      color: var(--tinta);
      margin: 0 0 4px;
    }
    .meta-txt {
      font-size: 12.5px;
      color: var(--gris);
    }
    .badge-garantia {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 16px;
      border-radius: 10px;
      font-size: 12.5px;
      max-width: 420px;
    }
    .badge-garantia.vigente {
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      color: #166534;
    }
    .badge-garantia.expirada {
      background: #fff1f2;
      border: 1px solid #fecdd3;
      color: #9f1239;
    }
    .icono-garantia {
      font-size: 24px;
    }
    .badge-garantia b {
      display: block;
      margin-bottom: 2px;
    }
    .sku-sub {
      display: block;
      font-family: var(--mono);
      font-size: 10.5px;
      color: var(--gris);
    }
    .inhabilitada {
      opacity: 0.55;
      background: #f8fafc;
    }
    .sin-cupo {
      color: var(--alerta);
    }
    .cant-input {
      width: 70px;
      padding: 5px 8px;
      font-size: 13px;
      text-align: center;
    }
    .panel-confirmacion {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 24px;
      margin-top: 22px;
      padding-top: 20px;
      border-top: 1px dashed var(--linea);
      flex-wrap: wrap;
    }
    .campos-motivo {
      display: flex;
      flex-direction: column;
      gap: 12px;
      flex: 1;
      min-width: 300px;
    }
    .resumen-reembolso {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 6px;
    }
    .label-reembolso {
      font-size: 12px;
      color: var(--gris);
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0.05em;
    }
    .monto-reembolso {
      font-size: 28px;
      font-weight: 800;
      color: var(--ganga);
      letter-spacing: -0.02em;
    }
    .btn-confirmar {
      padding: 10px 20px;
      font-size: 13.5px;
      margin-top: 8px;
    }
    .dev-comp {
      color: var(--ganga);
      font-family: var(--mono);
      font-size: 12px;
    }
    .tag-metodo {
      font-size: 11px;
      background: #f1f5f9;
      border: 1px solid var(--linea);
      border-radius: 4px;
      padding: 2px 6px;
      text-transform: uppercase;
    }
    .modal-devolucion {
      max-width: 440px;
    }
    .ticket-dev {
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.5;
    }
    .centro {
      text-align: center;
    }
    .espaciado {
      letter-spacing: 0.2em;
      font-weight: 800;
      font-size: 15px;
      margin-bottom: 2px;
    }
    .pequeno {
      font-size: 10.5px;
      color: var(--gris);
      margin-bottom: 14px;
    }
    .folio-dev {
      display: flex;
      justify-content: space-between;
      border-top: 1px dashed var(--linea);
      border-bottom: 1px dashed var(--linea);
      padding: 6px 0;
      margin-bottom: 10px;
    }
    .folio-dev b {
      color: var(--ganga);
    }
    .meta-ticket {
      font-size: 11px;
      color: var(--gris);
      margin-bottom: 12px;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .meta-ticket b {
      color: var(--tinta);
    }
    .items-dev-lista {
      border-top: 1px solid var(--linea);
      padding: 8px 0;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .fila-dev-item {
      display: flex;
      justify-content: space-between;
      font-size: 11.5px;
    }
    .total-dev-fila {
      display: flex;
      justify-content: space-between;
      border-top: 1.5px solid var(--tinta);
      padding-top: 8px;
      margin-top: 6px;
      font-size: 13.5px;
    }
    .total-dev-fila b {
      color: var(--ganga);
      font-size: 16px;
    }
    .reembolso-tipo {
      font-size: 11px;
      color: var(--gris);
      margin-top: 6px;
      text-align: right;
    }
    .aviso-stock-reintegrado {
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      border-radius: 6px;
      padding: 8px 10px;
      font-size: 10.5px;
      color: #166534;
      margin-top: 14px;
      text-align: center;
    }
  `,
})
export class DevolucionesComponent implements OnInit {
  private http = inject(HttpClient);
  private avisos = inject(Notificaciones);
  readonly sesion = inject(SesionStore);
  readonly sucursal = inject(SucursalActual);
  readonly moneda = moneda;

  vistaActiva = signal<'procesar' | 'historial'>('procesar');
  terminoBusqueda = '';
  readonly buscando = signal(false);
  readonly errorBusqueda = signal<string | null>(null);

  readonly venta = signal<VentaParaDevolucion | null>(null);
  motivo = '';
  metodoReembolso = 'efectivo';
  readonly procesando = signal(false);

  readonly devolucionEmitida = signal<DevolucionRegistrada | null>(null);

  readonly historial = signal<any[]>([]);
  readonly cargandoHistorial = signal(false);

  ngOnInit(): void {}

  buscarVenta(): void {
    const q = this.terminoBusqueda.trim();
    if (!q) return;

    this.buscando.set(true);
    this.errorBusqueda.set(null);
    this.venta.set(null);

    this.http.get<VentaParaDevolucion>(`${API_URL}/ventas/devoluciones/buscar?comprobante=${q}`).subscribe({
      next: (v) => {
        // Inicializar cada ítem con cantidad_a_devolver por defecto igual a la disponible
        for (const item of v.items) {
          item.seleccionado = false;
          item.cantidad_a_devolver = item.cantidad_disponible_devolucion;
        }
        this.venta.set(v);
        this.buscando.set(false);
      },
      error: (err) => {
        this.buscando.set(false);
        this.errorBusqueda.set(err.error?.detail ?? 'No se encontró ninguna venta con ese comprobante o ID.');
      },
    });
  }

  validarCantidad(item: ItemVentaDevolucion): void {
    const cant = item.cantidad_a_devolver || 1;
    if (cant > item.cantidad_disponible_devolucion) {
      item.cantidad_a_devolver = item.cantidad_disponible_devolucion;
      this.avisos.error(`Solo hay ${item.cantidad_disponible_devolucion} unidades disponibles para devolver.`);
    }
    if (cant < 1) {
      item.cantidad_a_devolver = 1;
    }
  }

  calcularTotal(): void {
    // Se recalcula automáticamente a través de la signal / método totalReembolso()
  }

  totalReembolso(): number {
    const v = this.venta();
    if (!v) return 0;
    return v.items
      .filter((i) => i.seleccionado)
      .reduce((sum, i) => sum + (i.cantidad_a_devolver || 1) * i.precio_unitario, 0);
  }

  confirmarDevolucion(): void {
    const v = this.venta();
    if (!v) return;

    const itemsSeleccionados = v.items
      .filter((i) => i.seleccionado && (i.cantidad_a_devolver || 0) > 0)
      .map((i) => ({
        variante_id: i.variante_id,
        cantidad: i.cantidad_a_devolver || 1,
        precio_unitario: i.precio_unitario,
      }));

    if (itemsSeleccionados.length === 0) {
      this.avisos.error('Marca al menos una prenda para procesar la devolución.');
      return;
    }

    if (!this.motivo.trim()) {
      this.avisos.error('Ingresa el motivo de la devolución.');
      return;
    }

    const sucursalId = this.sucursal.id() || v.sucursal_id;
    this.procesando.set(true);

    const payload = {
      venta_id: v.venta_id,
      sucursal_id: sucursalId,
      motivo: this.motivo.trim(),
      metodo_reembolso: this.metodoReembolso,
      items: itemsSeleccionados,
    };

    this.http.post<DevolucionRegistrada>(`${API_URL}/ventas/devoluciones`, payload).subscribe({
      next: (resultado) => {
        this.procesando.set(false);
        this.devolucionEmitida.set(resultado);
        this.avisos.ok(`✓ Devolución ${resultado.nro_comprobante} procesada y stock reintegrado con éxito.`);
        this.venta.set(null);
        this.terminoBusqueda = '';
        this.motivo = '';
      },
      error: (err) => {
        this.procesando.set(false);
        this.avisos.error(err.error?.detail ?? 'No se pudo procesar la devolución.');
      },
    });
  }

  cerrarModalComprobante(): void {
    this.devolucionEmitida.set(null);
  }

  imprimirTicket(): void {
    window.print();
  }

  cambiarAHistorial(): void {
    this.vistaActiva.set('historial');
    this.cargarHistorial();
  }

  cargarHistorial(): void {
    this.cargandoHistorial.set(true);
    const sucursalId = this.sucursal.id();
    let url = `${API_URL}/ventas/devoluciones`;
    if (sucursalId) url += `?sucursal_id=${sucursalId}`;

    this.http.get<any[]>(url).subscribe({
      next: (h) => {
        this.historial.set(h);
        this.cargandoHistorial.set(false);
      },
      error: () => {
        this.cargandoHistorial.set(false);
      },
    });
  }
}
