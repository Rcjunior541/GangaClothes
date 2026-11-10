import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { menuParaRoles } from './menu';

@Component({
  selector: 'app-admin-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './shell.html',
  styleUrl: './shell.css',
})
export class AdminShell {
  private auth = inject(AuthService);
  readonly sesion = this.auth.sesion;
  readonly menu = computed(() => menuParaRoles(this.sesion.roles(), this.sesion.permisos()));
  readonly sidebarAbierto = signal(false);

  /** El proveedor usa el mismo marco, pero no es personal de la tienda. */
  readonly subtitulo = computed(() => {
    const rol = this.sesion.rolPrincipal();
    if (rol === 'superadmin') return 'consola saas global';
    return rol === 'proveedor' ? 'portal de proveedores' : 'panel interno';
  });

  toggleSidebar(): void {
    this.sidebarAbierto.update((v) => !v);
  }

  cerrarSidebar(): void {
    this.sidebarAbierto.set(false);
  }

  salir(): void {
    this.auth.salir();
  }
}
