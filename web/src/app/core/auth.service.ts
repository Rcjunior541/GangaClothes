import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

import { API_URL } from './api';
import { rutaInicial } from './auth.guard';
import { SesionRespuesta, Usuario } from './modelos';
import { SesionStore } from './sesion';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  readonly sesion = inject(SesionStore);

  login(email: string, password: string, codigo_tenant?: string): Observable<SesionRespuesta> {
    const payload: { email: string; password: string; codigo_tenant?: string } = { email, password };
    if (codigo_tenant && codigo_tenant.trim()) {
      payload.codigo_tenant = codigo_tenant.trim().toLowerCase();
    }
    return this.http
      .post<SesionRespuesta>(`${API_URL}/auth/login`, payload)
      .pipe(tap((respuesta) => this.sesion.guardar(respuesta)));
  }

  registrar(datos: { nombre: string; apellido?: string; email: string; password: string; telefono?: string }) {
    return this.http
      .post<SesionRespuesta>(`${API_URL}/auth/register`, datos)
      .pipe(tap((respuesta) => this.sesion.guardar(respuesta)));
  }

  /** CU-01: Registrar una nueva empresa contratante (Tenant) con su admin y plan */
  registrarEmpresa(datos: any): Observable<any> {
    return this.http.post<any>(`${API_URL}/tenants/registro`, datos);
  }

  /** CU-01: Validar si el código alfanumérico de empresa está disponible */
  validarCodigoEmpresa(codigo: string): Observable<{ codigo: string; disponible: boolean; mensaje: string }> {
    return this.http.get<{ codigo: string; disponible: boolean; mensaje: string }>(
      `${API_URL}/tenants/validar-codigo/${encodeURIComponent(codigo)}`
    );
  }

  /** Pide el codigo de recuperacion. La API responde igual exista o no la cuenta. */
  recuperar(email: string): Observable<{ detail: string; minutos: number; reenvio_en: number }> {
    return this.http.post<{ detail: string; minutos: number; reenvio_en: number }>(`${API_URL}/auth/recuperar`, {
      email,
    });
  }

  restablecer(datos: { email: string; codigo: string; password: string }): Observable<{ detail: string }> {
    return this.http.post<{ detail: string }>(`${API_URL}/auth/restablecer`, datos);
  }

  /** Revalida el token contra la API; util al recargar la pagina. */
  yo(): Observable<Usuario> {
    return this.http.get<Usuario>(`${API_URL}/auth/me`);
  }

  salir(): void {
    // Se avisa al backend para que el cierre quede en la bitacora, pero la
    // sesion local se limpia igual: si el token ya vencio, salir no debe fallar.
    const token = this.sesion.token;
    if (token) {
      this.http.post(`${API_URL}/auth/logout`, {}).subscribe({ error: () => {} });
    }
    this.sesion.limpiar();
    this.router.navigate(['/login']);
  }

  /** Ruta a la que corresponde entrar segun los roles de la sesion actual. */
  rutaInicial(): string {
    return rutaInicial(this.sesion.roles());
  }
}
