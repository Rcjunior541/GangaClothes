import { CommonModule, DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { API_URL } from '../../../core/api';

export interface AdminResumen {
  id: number;
  nombre: string;
  apellido: string | null;
  email: string;
}

export interface PlanResumen {
  id: number;
  codigo: string;
  nombre: string;
  precio_mensual: number;
  limite_sucursales: number;
  permite_ia_generativa: boolean;
}

export interface SuscripcionResumen {
  id: number;
  plan_id: number;
  plan: PlanResumen;
  estado: string;
  fecha_inicio: string;
  fecha_vencimiento: string | null;
  ciclo_facturacion: string;
}

export interface Empresa {
  id: number;
  codigo: string;
  nombre: string;
  nit: string | null;
  telefono: string | null;
  direccion: string | null;
  pais: string;
  moneda: string;
  activo: boolean;
  fecha_creacion: string;
  suscripcion: SuscripcionResumen | null;
  admin: AdminResumen | null;
}

@Component({
  selector: 'app-empresas',
  standalone: true,
  imports: [CommonModule, FormsModule, DatePipe],
  template: `
    <div class="cabecera-seccion">
      <div>
        <span class="ceja">Superadministración SaaS</span>
        <h1>Empresas Contratantes (Tenants)</h1>
        <p class="subtitulo">Gestión global de espacios de trabajo, clientes SaaS y estado de sus suscripciones.</p>
      </div>
      <div class="contador-badge">
        Total: <b>{{ empresas().length }}</b> empresas
      </div>
    </div>

    <div class="filtros-barra">
      <input
        type="text"
        class="campo busqueda"
        placeholder="Buscar por nombre, código o correo de admin..."
        [(ngModel)]="busqueda"
      />
    </div>

    @if (cargando()) {
      <div class="mensaje">Cargando empresas registradas...</div>
    } @else if (error()) {
      <div class="mensaje error">{{ error() }}</div>
    } @else if (filtradas().length === 0) {
      <div class="mensaje vacio">No se encontraron empresas contratantes.</div>
    } @else {
      <div class="marco-tabla">
        <table>
          <thead>
            <tr>
              <th class="col-indice">ID</th>
              <th>Código</th>
              <th>Empresa</th>
              <th>Administrador</th>
              <th>Plan</th>
              <th>Suscripción</th>
              <th>Fecha de Alta</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            @for (empresa of filtradas(); track empresa.id) {
              <tr>
                <td class="col-indice">#{{ empresa.id }}</td>
                <td>
                  <span class="badge-codigo">{{ empresa.codigo }}</span>
                </td>
                <td>
                  <div class="datos-empresa">
                    <b>{{ empresa.nombre }}</b>
                    @if (empresa.nit) {
                      <small>NIT: {{ empresa.nit }}</small>
                    }
                  </div>
                </td>
                <td>
                  @if (empresa.admin) {
                    <div class="datos-admin">
                      <span>{{ empresa.admin.nombre }} {{ empresa.admin.apellido ?? '' }}</span>
                      <small>{{ empresa.admin.email }}</small>
                    </div>
                  } @else {
                    <span class="sin-dato">—</span>
                  }
                </td>
                <td>
                  @if (empresa.suscripcion?.plan) {
                    <span class="plan-tag" [class.profesional]="empresa.suscripcion?.plan?.codigo === 'profesional'">
                      {{ empresa.suscripcion?.plan?.nombre }}
                    </span>
                  } @else {
                    <span class="sin-dato">Sin plan</span>
                  }
                </td>
                <td>
                  @if (empresa.suscripcion) {
                    <span
                      class="estado"
                      [class.ok]="empresa.suscripcion.estado === 'activa'"
                      [class.bajo]="empresa.suscripcion.estado === 'vencida' || empresa.suscripcion.estado === 'cancelada'"
                    >
                      {{ empresa.suscripcion.estado }}
                    </span>
                    @if (empresa.suscripcion.fecha_vencimiento) {
                      <div class="vence-txt">
                        Vence: {{ empresa.suscripcion.fecha_vencimiento | date: 'dd/MM/yyyy' }}
                      </div>
                    }
                  } @else {
                    <span class="sin-dato">—</span>
                  }
                </td>
                <td>
                  {{ empresa.fecha_creacion | date: 'dd/MM/yyyy HH:mm' }}
                </td>
                <td>
                  <span class="estado" [class.ok]="empresa.activo" [class.bajo]="!empresa.activo">
                    {{ empresa.activo ? 'Activa' : 'Inactiva' }}
                  </span>
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
      margin-bottom: 24px;
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
      max-width: 650px;
    }
    .contador-badge {
      background: #ffffff;
      border: 1px solid var(--linea);
      border-radius: 8px;
      padding: 6px 14px;
      font-size: 13px;
      color: var(--gris);
      box-shadow: var(--sombra-sm);
    }
    .contador-badge b {
      color: var(--ganga);
    }
    .filtros-barra {
      margin-bottom: 18px;
    }
    .busqueda {
      max-width: 420px;
    }
    .badge-codigo {
      display: inline-block;
      font-family: var(--mono);
      font-size: 11.5px;
      font-weight: 700;
      background: var(--papel);
      color: var(--tinta);
      border: 1px solid var(--linea);
      border-radius: 6px;
      padding: 2px 8px;
    }
    .datos-empresa, .datos-admin {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .datos-empresa small, .datos-admin small {
      font-size: 11px;
      color: var(--gris);
    }
    .plan-tag {
      display: inline-flex;
      font-size: 11px;
      font-weight: 700;
      border-radius: 6px;
      padding: 2px 8px;
      background: #f1f5f9;
      color: #334155;
      border: 1px solid #cbd5e1;
    }
    .plan-tag.profesional {
      background: var(--ganga-suave);
      color: var(--ganga);
      border-color: var(--ganga-borde);
    }
    .vence-txt {
      font-size: 10.5px;
      color: var(--gris);
      margin-top: 3px;
    }
    .sin-dato {
      color: var(--gris-claro);
      font-size: 12px;
    }
  `,
})
export class EmpresasComponent implements OnInit {
  private http = inject(HttpClient);

  readonly empresas = signal<Empresa[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  busqueda = '';

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.http.get<Empresa[]>(`${API_URL}/tenants`).subscribe({
      next: (datos) => {
        this.empresas.set(datos);
        this.cargando.set(false);
      },
      error: (err) => {
        this.error.set('No se pudo cargar el listado de empresas. Verifica tus credenciales de superadmin.');
        this.cargando.set(false);
      },
    });
  }

  filtradas(): Empresa[] {
    const q = this.busqueda.trim().toLowerCase();
    if (!q) return this.empresas();
    return this.empresas().filter(
      (e) =>
        e.nombre.toLowerCase().includes(q) ||
        e.codigo.toLowerCase().includes(q) ||
        (e.admin && e.admin.email.toLowerCase().includes(q)),
    );
  }
}
