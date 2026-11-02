import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Subject, debounceTime, distinctUntilChanged, filter, switchMap } from 'rxjs';

import { AuthService } from '../../../core/auth.service';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { contrasenaSegura, contrasenasIguales, ReglasContrasena } from '../../../shared/contrasena/reglas-contrasena';

const TELEFONO = /^[0-9+\-\s]{6,20}$/;
const CODIGO_REGEX = /^[a-z0-9-]+$/;

type Campo =
  | 'codigo_tenant'
  | 'nombre_empresa'
  | 'nit'
  | 'telefono'
  | 'direccion'
  | 'plan_codigo'
  | 'ciclo_facturacion'
  | 'admin_nombre'
  | 'admin_apellido'
  | 'admin_email'
  | 'admin_password'
  | 'confirmar_password';

@Component({
  selector: 'app-registro-tenant',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink, ReglasContrasena],
  templateUrl: './registro-tenant.html',
  styleUrl: './registro-tenant.css',
})
export class RegistroTenant {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);
  private avisos = inject(Notificaciones);

  readonly enviando = signal(false);
  readonly error = signal<string | null>(null);

  // Validación de disponibilidad de código en tiempo real
  readonly codigoVerificando = signal(false);
  readonly codigoDisponible = signal<boolean | null>(null);
  readonly codigoMensaje = signal<string | null>(null);
  private codigoSubject = new Subject<string>();

  readonly formulario = this.fb.nonNullable.group(
    {
      // Datos de la Empresa
      codigo_tenant: [
        '',
        [
          Validators.required,
          Validators.minLength(3),
          Validators.maxLength(50),
          Validators.pattern(CODIGO_REGEX),
        ],
      ],
      nombre_empresa: ['', [Validators.required, Validators.maxLength(150), Validators.pattern(/\S/)]],
      nit: ['', [Validators.maxLength(30)]],
      telefono: ['', [Validators.pattern(TELEFONO)]],
      direccion: ['', [Validators.maxLength(250)]],

      // Suscripción
      plan_codigo: ['basico', [Validators.required]],
      ciclo_facturacion: ['mensual', [Validators.required]],

      // Administrador Inicial
      admin_nombre: ['', [Validators.required, Validators.maxLength(100), Validators.pattern(/\S/)]],
      admin_apellido: ['', [Validators.maxLength(100)]],
      admin_email: ['', [Validators.required, Validators.email, Validators.maxLength(120)]],
      admin_password: ['', [Validators.required, Validators.maxLength(72), contrasenaSegura]],
      confirmar_password: ['', [Validators.required]],
    },
    { validators: contrasenasIguales },
  );

  constructor() {
    // Escuchar cambios en el código de empresa con debounce
    this.codigoSubject
      .pipe(
        debounceTime(350),
        distinctUntilChanged(),
        filter((c) => c.length >= 3 && CODIGO_REGEX.test(c)),
        switchMap((codigo) => {
          this.codigoVerificando.set(true);
          return this.auth.validarCodigoEmpresa(codigo);
        }),
      )
      .subscribe({
        next: (res) => {
          this.codigoVerificando.set(false);
          this.codigoDisponible.set(res.disponible);
          this.codigoMensaje.set(res.mensaje);
        },
        error: () => {
          this.codigoVerificando.set(false);
          this.codigoDisponible.set(null);
        },
      });
  }

  onCodigoInput(evento: Event): void {
    const input = evento.target as HTMLInputElement;
    const limpio = input.value.trim().toLowerCase();
    this.formulario.controls.codigo_tenant.setValue(limpio, { emitEvent: false });
    this.codigoDisponible.set(null);
    this.codigoMensaje.set(null);
    if (limpio.length >= 3 && CODIGO_REGEX.test(limpio)) {
      this.codigoSubject.next(limpio);
    }
  }

  seleccionarPlan(codigo: string): void {
    this.formulario.controls.plan_codigo.setValue(codigo);
  }

  seleccionarCiclo(ciclo: string): void {
    this.formulario.controls.ciclo_facturacion.setValue(ciclo);
  }

  invalido(campo: Campo): boolean {
    const control = this.formulario.controls[campo];
    return control.invalid && (control.dirty || control.touched);
  }

  distintas(): boolean {
    const confirmar = this.formulario.controls.confirmar_password;
    return (confirmar.dirty || confirmar.touched) && this.formulario.hasError('distintas');
  }

  enviar(): void {
    this.error.set(null);
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    if (this.codigoDisponible() === false) {
      this.error.set('El código de empresa elegido ya está ocupado. Por favor cámbielo.');
      return;
    }

    const crudo = this.formulario.getRawValue();
    this.enviando.set(true);

    const payload = {
      codigo_tenant: crudo.codigo_tenant,
      nombre_empresa: crudo.nombre_empresa,
      nit: crudo.nit || undefined,
      telefono: crudo.telefono || undefined,
      direccion: crudo.direccion || undefined,
      pais: 'Bolivia',
      moneda: 'BOB',
      plan_codigo: crudo.plan_codigo,
      ciclo_facturacion: crudo.ciclo_facturacion,
      admin_nombre: crudo.admin_nombre,
      admin_apellido: crudo.admin_apellido || undefined,
      admin_email: crudo.admin_email,
      admin_password: crudo.admin_password,
    };

    this.auth.registrarEmpresa(payload).subscribe({
      next: (tenantCreado) => {
        this.enviando.set(false);
        this.avisos.ok(
          `¡Empresa ${tenantCreado.nombre} registrada con éxito! Ya puedes iniciar sesión.`,
        );
        this.router.navigate(['/login'], {
          queryParams: { tenant: tenantCreado.codigo, email: crudo.admin_email },
        });
      },
      error: (err) => {
        this.enviando.set(false);
        this.error.set(mensajeDeError(err, 'No se pudo completar el registro de la empresa'));
      },
    });
  }
}
