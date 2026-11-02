import { CommonModule, DatePipe } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';

import { IndexedDbService, VentaOffline } from '../../../core/offline/indexed-db.service';
import { Notificaciones } from '../../../core/notificaciones';
import { moneda } from '../../../shared/formato';

@Component({
  selector: 'app-bandeja-pendientes',
  standalone: true,
  imports: [CommonModule, DatePipe],
  template: `
    <div class="cabecera-seccion">
      <div>
        <span class="ceja">PWA & Operación Offline</span>
        <h1>Bandeja de Sincronización Local (CU-15)</h1>
        <p class="subtitulo">
          Control de ventas procesadas sin conexión en este dispositivo y su estado de consolidación con el servidor central.
        </p>
      </div>

      <div class="acciones-cabecera">
        <button
          type="button"
          class="btn rosa"
          (click)="sincronizar()"
          [disabled]="sincronizando() || !offline.online() || pendientesCount() === 0"
        >
          {{ sincronizando() ? 'Sincronizando lote...' : '🔄 Sincronizar Ahora (CU-16)' }}
        </button>
      </div>
    </div>

    @if (!offline.online()) {
      <div class="banner-aviso offline">
        <b>📶 Modo Sin Conexión Activo</b>
        <span>Las ventas se mantendrán almacenadas en IndexedDB hasta que se restablezca la conexión a Internet.</span>
      </div>
    }

    <!-- Tarjetas de métricas -->
    <div class="metricas-grid">
      <div class="metrica-tarjeta">
        <span class="metrica-num">{{ operaciones().length }}</span>
        <span class="metrica-label">Total en este dispositivo</span>
      </div>
      <div class="metrica-tarjeta alerta">
        <span class="metrica-num">{{ pendientesCount() }}</span>
        <span class="metrica-label">Pendientes (LOCAL)</span>
      </div>
      <div class="metrica-tarjeta ok">
        <span class="metrica-num">{{ confirmadasCount() }}</span>
        <span class="metrica-label">Confirmadas en Servidor</span>
      </div>
      <div class="metrica-tarjeta error">
        <span class="metrica-num">{{ conflictosCount() }}</span>
        <span class="metrica-label">En Conflicto (CU-17)</span>
      </div>
    </div>

    @if (cargando()) {
      <div class="mensaje">Leyendo almacenamiento local IndexedDB...</div>
    } @else if (operaciones().length === 0) {
      <div class="mensaje vacio">
        <p>No hay operaciones registradas en el almacenamiento local.</p>
        <small>Las ventas que realices en Caja cuando no haya conexión aparecerán aquí automáticamente.</small>
      </div>
    } @else {
      <div class="marco-tabla">
        <table>
          <thead>
            <tr>
              <th>UUID de Operación</th>
              <th>Sucursal</th>
              <th>Fecha y Hora</th>
              <th>Prendas / Ítems</th>
              <th>Total Cobrado</th>
              <th>Estado</th>
              <th>Comprobante Central</th>
            </tr>
          </thead>
          <tbody>
            @for (op of operaciones(); track op.uuid_operacion) {
              <tr [class.fila-conflicto]="op.estado === 'EN_CONFLICTO'">
                <td>
                  <span class="uuid-badge" [title]="op.uuid_operacion">
                    {{ op.uuid_operacion.substring(0, 13) }}...
                  </span>
                </td>
                <td>{{ op.sucursal_nombre ?? 'Sucursal #' + op.sucursal_id }}</td>
                <td>{{ op.fecha_hora | date: 'dd/MM/yyyy HH:mm:ss' }}</td>
                <td>
                  <div class="lista-items">
                    @for (item of op.items; track item.sku) {
                      <span class="item-tag">
                        {{ item.cantidad }}× {{ item.prenda_nombre }} ({{ item.talla }}/{{ item.color }})
                      </span>
                    }
                  </div>
                </td>
                <td>
                  <b>Bs {{ moneda(op.total) }}</b>
                  <small class="pago-txt">Efectivo</small>
                </td>
                <td>
                  <span
                    class="estado"
                    [class.ok]="op.estado === 'CONFIRMADA'"
                    [class.bajo]="op.estado === 'LOCAL'"
                    [class.error-badge]="op.estado === 'EN_CONFLICTO' || op.estado === 'RECHAZADA'"
                  >
                    {{ op.estado }}
                  </span>
                  @if (op.mensaje_servidor) {
                    <div class="mensaje-servidor-txt" [class.txt-err]="op.estado === 'EN_CONFLICTO'">
                      {{ op.mensaje_servidor }}
                    </div>
                  }
                </td>
                <td>
                  @if (op.nro_comprobante) {
                    <b class="nro-comp">{{ op.nro_comprobante }}</b>
                  } @else {
                    <span class="sin-dato">Pendiente</span>
                  }
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    }
  `,
  styles: `
    .cabecera-seccion {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      margin-bottom: 22px;
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
      max-width: 650px;
    }
    .banner-aviso {
      background: #fffbeb;
      border: 1px solid #fde68a;
      border-left: 4px solid #f59e0b;
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 18px;
      font-size: 13px;
      color: #92400e;
    }
    .banner-aviso b {
      display: block;
      margin-bottom: 2px;
    }
    .metricas-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin-bottom: 22px;
    }
    .metrica-tarjeta {
      background: #ffffff;
      border: 1px solid var(--linea);
      border-radius: 12px;
      padding: 16px 20px;
      box-shadow: var(--sombra-sm);
      display: flex;
      flex-direction: column;
    }
    .metrica-tarjeta.alerta {
      border-left: 4px solid #f59e0b;
    }
    .metrica-tarjeta.ok {
      border-left: 4px solid var(--ok);
    }
    .metrica-tarjeta.error {
      border-left: 4px solid var(--alerta);
    }
    .metrica-num {
      font-size: 26px;
      font-weight: 800;
      color: var(--tinta);
    }
    .metrica-label {
      font-size: 12px;
      color: var(--gris);
      margin-top: 2px;
    }
    .uuid-badge {
      font-family: var(--mono);
      font-size: 11px;
      background: var(--papel);
      border: 1px solid var(--linea);
      border-radius: 4px;
      padding: 2px 6px;
      color: var(--tinta);
    }
    .lista-items {
      display: flex;
      flex-direction: column;
      gap: 3px;
    }
    .item-tag {
      font-size: 11.5px;
      color: var(--tinta);
    }
    .pago-txt {
      display: block;
      font-size: 11px;
      color: var(--gris);
    }
    .nro-comp {
      color: var(--ganga);
      font-size: 12px;
    }
    .sin-dato {
      color: var(--gris-claro);
      font-size: 11.5px;
    }
    .error-badge {
      background: #fff1f2;
      color: var(--alerta);
      border: 1px solid #fecdd3;
    }
    .mensaje-servidor-txt {
      font-size: 10.5px;
      color: var(--gris);
      margin-top: 3px;
    }
    .mensaje-servidor-txt.txt-err {
      color: var(--alerta);
      font-weight: 600;
    }
    .fila-conflicto {
      background: #fff7ed;
    }
  `,
})
export class BandejaPendientesComponent implements OnInit {
  readonly offline = inject(IndexedDbService);
  private avisos = inject(Notificaciones);
  readonly moneda = moneda;

  readonly operaciones = signal<VentaOffline[]>([]);
  readonly cargando = signal(true);
  readonly sincronizando = signal(false);

  readonly pendientesCount = signal(0);
  readonly confirmadasCount = signal(0);
  readonly conflictosCount = signal(0);

  ngOnInit(): void {
    this.cargar();
  }

  async cargar(): Promise<void> {
    this.cargando.set(true);
    const ops = await this.offline.obtenerTodasOperaciones();
    this.operaciones.set(ops.reverse());

    this.pendientesCount.set(ops.filter((o) => o.estado === 'LOCAL').length);
    this.confirmadasCount.set(ops.filter((o) => o.estado === 'CONFIRMADA').length);
    this.conflictosCount.set(ops.filter((o) => o.estado === 'EN_CONFLICTO').length);
    this.cargando.set(false);
  }

  async sincronizar(): Promise<void> {
    if (!this.offline.online()) {
      this.avisos.error('No hay conexión a internet para sincronizar.');
      return;
    }
    this.sincronizando.set(true);
    try {
      const res = await this.offline.sincronizarLote();
      if (res) {
        if (res.conflictos > 0) {
          this.avisos.error(
            `Sincronización con ${res.conflictos} conflicto(s) de stock. Revisa los detalles en pantalla.`,
          );
        } else {
          this.avisos.ok(`✓ Lote sincronizado: ${res.confirmadas} venta(s) confirmadas en el servidor.`);
        }
      } else {
        this.avisos.ok('No hay operaciones pendientes de sincronizar.');
      }
      await this.cargar();
    } catch {
      this.avisos.error('Error al conectar con el servidor de sincronización.');
    } finally {
      this.sincronizando.set(false);
    }
  }
}
