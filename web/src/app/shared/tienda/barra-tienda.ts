import { Component, computed, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { SesionStore } from '../../core/sesion';

/**
 * Barra superior de la tienda en linea: catalogo, compras, reservas y carrito del cliente.
 * Uso: `<app-barra-tienda />`.
 */
@Component({
  selector: 'app-barra-tienda',
  imports: [RouterLink, RouterLinkActive],
  template: `
    <header class="topnav">
      <a class="logo" routerLink="/catalogo">Ganga<b>Clothes</b></a>
      <nav class="secciones">
        <a routerLink="/catalogo" routerLinkActive="on">Catalogo</a>
        @if (esCliente()) {
          <a routerLink="/mis-reservas" routerLinkActive="on">Mis reservas</a>
          <a routerLink="/mis-compras" routerLinkActive="on">Mis compras</a>
          <a routerLink="/mis-envios" routerLinkActive="on">Mis pedidos</a>
          <a routerLink="/carrito" routerLinkActive="on">Carrito</a>
        }
      </nav>

      @if (sesion.autenticado()) {
        <span class="yo">{{ sesion.nombreCompleto() }} · {{ sesion.rolPrincipal() }}</span>
        @if (esPersonal()) {
          <a class="btn linea acceso" routerLink="/admin">Ir al panel</a>
        }
        <button type="button" class="btn linea acceso" (click)="auth.salir()">Cerrar sesion</button>
      } @else {
        <a class="btn linea acceso invitado" routerLink="/login" [queryParams]="volver()">Iniciar sesion</a>
        <a class="btn rosa acceso" routerLink="/registro" [queryParams]="volver()">Crear cuenta</a>
      }
    </header>
  `,
  styles: `
    .topnav {
      display: flex;
      align-items: center;
      gap: 18px;
      flex-wrap: wrap;
      padding: 14px 28px;
      background: #fff;
      border-bottom: 1px solid var(--linea);
      box-shadow: var(--sombra-sm);
    }
    .logo {
      font-size: 17px;
    }
    .secciones {
      display: flex;
      gap: 20px;
    }
    .secciones a {
      font-size: 13px;
      font-weight: 500;
      color: var(--gris);
      padding: 4px 0;
      border-bottom: 2px solid transparent;
      transition: all 0.15s ease;
    }
    .secciones a:hover {
      color: var(--tinta);
    }
    .secciones a.on {
      color: var(--ganga);
      font-weight: 700;
      border-bottom-color: var(--ganga);
    }
    .yo {
      margin-left: auto;
      font-family: var(--sans);
      font-size: 11px;
      font-weight: 500;
      background: var(--papel);
      border: 1px solid var(--linea);
      border-radius: 8px;
      padding: 5px 12px;
      color: var(--gris);
    }
    .acceso {
      padding: 6px 13px;
      font-size: 11.5px;
    }
    .invitado {
      margin-left: auto;
    }
  `,
})
export class BarraTienda {
  readonly auth = inject(AuthService);
  readonly sesion = inject(SesionStore);
  private router = inject(Router);

  readonly esCliente = computed(() => this.sesion.tieneAlgunRol('cliente'));
  readonly esPersonal = computed(() => this.sesion.tieneAlgunRol('administrador', 'encargado', 'cajero'));

  /** Despues de entrar o registrarse, vuelve a la pagina donde estaba. */
  volver(): Record<string, string> {
    const url = this.router.url;
    return url.startsWith('/login') || url.startsWith('/registro') ? {} : { volverA: url };
  }
}
