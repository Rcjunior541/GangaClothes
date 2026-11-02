import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { SesionStore } from '../../../core/sesion';

export interface PlanDetalle {
  id: number;
  codigo: string;
  nombre: string;
  precio_mensual: number;
  limite_sucursales: number;
  permite_ia_generativa: boolean;
  descripcion: string | null;
  activo: boolean;
}

export interface MiSuscripcion {
  tenant_id: number;
  empresa_nombre: string;
  codigo_tenant: string;
  estado: string;
  ciclo_facturacion: string;
  fecha_inicio: string;
  fecha_vencimiento: string | null;
  dias_restantes: number | null;
  por_vencer: boolean;
  plan_actual: PlanDetalle;
  sucursales_activas: number;
  limite_sucursales: number;
  cupos_disponibles: number;
  permite_ia_generativa: boolean;
  planes_disponibles: PlanDetalle[];
}

@Component({
  selector: 'app-suscripcion',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './suscripcion.html',
  styleUrls: ['./suscripcion.css'],
})
export class SuscripcionComponent implements OnInit {
  private http = inject(HttpClient);
  private avisos = inject(Notificaciones);
  readonly sesion = inject(SesionStore);

  readonly suscripcion = signal<MiSuscripcion | null>(null);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);

  // Modal para cambio de plan
  readonly modalCambioAbierto = signal(false);
  readonly cambiandoPlan = signal(false);
  readonly planSeleccionado = signal<string>('basico');
  readonly cicloSeleccionado = signal<string>('mensual');
  readonly errorCambio = signal<string | null>(null);

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.http.get<MiSuscripcion>(`${API_URL}/suscripciones/mi-suscripcion`).subscribe({
      next: (data) => {
        this.suscripcion.set(data);
        this.planSeleccionado.set(data.plan_actual.codigo);
        this.cicloSeleccionado.set(data.ciclo_facturacion);
        this.cargando.set(false);
      },
      error: (err) => {
        this.error.set(mensajeDeError(err, 'No se pudo cargar la información de la suscripción'));
        this.cargando.set(false);
      },
    });
  }

  abrirModalCambio(): void {
    const actual = this.suscripcion();
    if (actual) {
      this.planSeleccionado.set(actual.plan_actual.codigo);
      this.cicloSeleccionado.set(actual.ciclo_facturacion);
    }
    this.errorCambio.set(null);
    this.modalCambioAbierto.set(true);
  }

  cerrarModal(): void {
    this.modalCambioAbierto.set(false);
    this.errorCambio.set(null);
  }

  confirmarCambio(): void {
    this.cambiandoPlan.set(true);
    this.errorCambio.set(null);

    const payload = {
      plan_codigo: this.planSeleccionado(),
      ciclo_facturacion: this.cicloSeleccionado(),
    };

    this.http.post<MiSuscripcion>(`${API_URL}/suscripciones/cambiar-plan`, payload).subscribe({
      next: (actualizada) => {
        this.suscripcion.set(actualizada);
        this.cambiandoPlan.set(false);
        this.modalCambioAbierto.set(false);
        this.avisos.ok(`¡Plan actualizado con éxito al ${actualizada.plan_actual.nombre}!`);
      },
      error: (err) => {
        this.cambiandoPlan.set(false);
        this.errorCambio.set(mensajeDeError(err, 'No se pudo realizar el cambio de plan'));
      },
    });
  }
}
