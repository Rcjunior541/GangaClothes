import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';

import { API_URL } from '../../../core/api';
import { Notificaciones } from '../../../core/notificaciones';

export interface PlanSaaS {
  id: number;
  codigo: string;
  nombre: string;
  precio_mensual: number;
  limite_sucursales: number;
  permite_ia_generativa: boolean;
  descripcion: string | null;
  activo: boolean;
}

@Component({
  selector: 'app-planes',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="cabecera-seccion">
      <div>
        <span class="ceja">Superadministración SaaS</span>
        <h1>Planes de Suscripción</h1>
        <p class="subtitulo">Configuración de niveles de servicio, precios mensuales y límites de sucursales del ecosistema.</p>
      </div>
    </div>

    @if (cargando()) {
      <div class="mensaje">Cargando planes de suscripción...</div>
    } @else if (error()) {
      <div class="mensaje error">{{ error() }}</div>
    } @else {
      <div class="grilla-planes">
        @for (plan of planes(); track plan.id) {
          <div class="tarjeta-plan" [class.destacada]="plan.codigo === 'profesional'">
            <div class="plan-top">
              <span class="plan-codigo">{{ plan.codigo }}</span>
              <span class="estado" [class.ok]="plan.activo" [class.bajo]="!plan.activo">
                {{ plan.activo ? 'Activo' : 'Inactivo' }}
              </span>
            </div>

            <h2>{{ plan.nombre }}</h2>
            <div class="precio">
              Bs {{ plan.precio_mensual }} <small>/mes</small>
            </div>

            <p class="desc">{{ plan.descripcion }}</p>

            <ul class="caracteristicas">
              <li>
                <b>Límite de sucursales:</b> {{ plan.limite_sucursales }} sucursales activas
              </li>
              <li>
                <b>Reportes con IA Generativa:</b>
                <span class="badge-ia" [class.on]="plan.permite_ia_generativa">
                  {{ plan.permite_ia_generativa ? 'Habilitado' : 'No disponible' }}
                </span>
              </li>
              <li><b>Sincronización Multitenant:</b> Incluida</li>
              <li><b>Gestión de Inventario y Ventas:</b> Incluida</li>
            </ul>

            <button type="button" class="btn linea bloque" (click)="abrirEditar(plan)">
              Editar Parámetros
            </button>
          </div>
        }
      </div>
    }

    <!-- Modal para editar parámetros del plan -->
    @if (modalAbierto()) {
      <div class="fondo" (click)="cerrarModal()">
        <div class="modal" (click)="$event.stopPropagation()">
          <h2>Editar Plan: {{ planEditando()?.nombre }}</h2>

          <form [formGroup]="formulario" (ngSubmit)="guardarCambios()" novalidate>
            <div class="rejilla">
              <div class="grupo completo">
                <label class="etiqueta" for="p-nombre">Nombre Comercial</label>
                <input id="p-nombre" type="text" class="campo" formControlName="nombre" />
              </div>

              <div class="grupo">
                <label class="etiqueta" for="p-precio">Precio Mensual (Bs)</label>
                <input id="p-precio" type="number" step="0.01" class="campo" formControlName="precio_mensual" />
              </div>

              <div class="grupo">
                <label class="etiqueta" for="p-limite">Límite de Sucursales</label>
                <input id="p-limite" type="number" class="campo" formControlName="limite_sucursales" />
              </div>

              <div class="grupo completo">
                <label class="etiqueta" for="p-desc">Descripción</label>
                <textarea id="p-desc" class="campo" rows="3" formControlName="descripcion"></textarea>
              </div>

              <div class="grupo completo check-ia">
                <label>
                  <input type="checkbox" formControlName="permite_ia_generativa" />
                  Permitir Reportes con Inteligencia Artificial Generativa
                </label>
              </div>
            </div>

            @if (errorForm()) {
              <div class="error-servidor">{{ errorForm() }}</div>
            }

            <div class="acciones">
              <button type="button" class="btn linea" (click)="cerrarModal()">Cancelar</button>
              <button type="submit" class="btn rosa" [disabled]="guardando()">
                {{ guardando() ? 'Guardando...' : 'Guardar Cambios' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    }
  `,
  styles: `
    .cabecera-seccion {
      margin-bottom: 24px;
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
    .grilla-planes {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 22px;
      max-width: 900px;
    }
    .tarjeta-plan {
      background: #ffffff;
      border: 1.5px solid var(--linea);
      border-radius: 14px;
      padding: 26px;
      box-shadow: var(--sombra-sm);
      display: flex;
      flex-direction: column;
      transition: all 0.2s ease;
    }
    .tarjeta-plan:hover {
      box-shadow: var(--sombra-md);
      transform: translateY(-2px);
    }
    .tarjeta-plan.destacada {
      border-color: var(--ganga);
      box-shadow: 0 4px 14px rgba(5, 150, 105, 0.12);
    }
    .plan-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .plan-codigo {
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--gris);
      background: var(--papel);
      padding: 2px 8px;
      border-radius: 4px;
      border: 1px solid var(--linea);
    }
    .tarjeta-plan h2 {
      font-size: 20px;
      font-weight: 800;
      color: var(--tinta);
      margin-bottom: 6px;
    }
    .precio {
      font-size: 28px;
      font-weight: 800;
      color: var(--ganga);
      margin-bottom: 12px;
    }
    .precio small {
      font-size: 13px;
      font-weight: 500;
      color: var(--gris);
    }
    .desc {
      font-size: 13px;
      color: var(--gris);
      line-height: 1.5;
      margin-bottom: 18px;
      min-height: 40px;
    }
    .caracteristicas {
      list-style: none;
      padding: 0;
      margin: 0 0 24px;
      font-size: 13px;
      color: var(--tinta);
      display: flex;
      flex-direction: column;
      gap: 10px;
      flex: 1;
    }
    .caracteristicas li {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px dashed var(--linea);
      padding-bottom: 8px;
    }
    .badge-ia {
      font-size: 11px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 999px;
      background: #f1f5f9;
      color: #64748b;
    }
    .badge-ia.on {
      background: var(--ganga-suave);
      color: var(--ganga);
      border: 1px solid var(--ganga-borde);
    }
    .check-ia label {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      font-weight: 600;
      color: var(--tinta);
      cursor: pointer;
    }
    .check-ia input {
      accent-color: var(--ganga);
      width: 16px;
      height: 16px;
    }
  `,
})
export class PlanesComponent implements OnInit {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private avisos = inject(Notificaciones);

  readonly planes = signal<PlanSaaS[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);

  readonly modalAbierto = signal(false);
  readonly planEditando = signal<PlanSaaS | null>(null);
  readonly guardando = signal(false);
  readonly errorForm = signal<string | null>(null);

  readonly formulario: FormGroup = this.fb.group({
    nombre: ['', [Validators.required]],
    precio_mensual: [0, [Validators.required, Validators.min(0)]],
    limite_sucursales: [1, [Validators.required, Validators.min(1)]],
    descripcion: [''],
    permite_ia_generativa: [false],
  });

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.http.get<PlanSaaS[]>(`${API_URL}/suscripciones/planes?solo_activos=false`).subscribe({
      next: (datos) => {
        this.planes.set(datos);
        this.cargando.set(false);
      },
      error: () => {
        this.error.set('No se pudo cargar el catálogo de planes.');
        this.cargando.set(false);
      },
    });
  }

  abrirEditar(plan: PlanSaaS): void {
    this.planEditando.set(plan);
    this.errorForm.set(null);
    this.formulario.reset({
      nombre: plan.nombre,
      precio_mensual: plan.precio_mensual,
      limite_sucursales: plan.limite_sucursales,
      descripcion: plan.descripcion,
      permite_ia_generativa: plan.permite_ia_generativa,
    });
    this.modalAbierto.set(true);
  }

  cerrarModal(): void {
    this.modalAbierto.set(false);
    this.planEditando.set(null);
  }

  guardarCambios(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    const plan = this.planEditando();
    if (!plan) return;

    this.guardando.set(true);
    this.errorForm.set(null);
    this.http.put<PlanSaaS>(`${API_URL}/suscripciones/planes/${plan.id}`, this.formulario.value).subscribe({
      next: (actualizado) => {
        this.planes.update((lista) => lista.map((p) => (p.id === actualizado.id ? actualizado : p)));
        this.guardando.set(false);
        this.cerrarModal();
        this.avisos.ok(`Plan '${actualizado.nombre}' actualizado con éxito`);
      },
      error: (err) => {
        this.guardando.set(false);
        this.errorForm.set(err.error?.detail ?? 'No se pudo actualizar el plan.');
      },
    });
  }
}
