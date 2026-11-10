import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { API_URL } from '../../../core/api';
import { Notificaciones } from '../../../core/notificaciones';
import { SesionStore } from '../../../core/sesion';
import { moneda } from '../../../shared/formato';

export interface ReporteGenerado {
  titulo: string;
  resumen_narrativo: string;
  tipo_grafico: 'barras' | 'lineas' | 'torta' | 'tabla';
  columnas: string[];
  filas: Record<string, any>[];
  datos_grafico: Array<{ etiqueta: string; valor: number }>;
  total_registros: number;
  consulta_original: string;
  fecha_generacion: string;
}

@Component({
  selector: 'app-reporte-generativo',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="cabecera-seccion">
      <div>
        <span class="ceja">Hito 3 · Inteligencia Artificial Generativa</span>
        <h1>Reportes Inteligentes con IA (CU-19)</h1>
        <p class="subtitulo">
          Escribe o dicta por voz tu consulta en lenguaje natural. La IA estructurará y consolidará los datos de tu empresa con gráficos y exportación.
        </p>
      </div>

      <div class="badge-plan-prof">
        <span>Plan Profesional</span>
      </div>
    </div>

    <!-- 1. BLOQUE DE ENTRADA (TEXTO O MICRÓFONO) -->
    <div class="bloque-consulta">
      <div class="barra-input-voz">
        <input
          type="text"
          class="campo input-prompt"
          placeholder="Escribe o dicta lo que necesitas (ej: 'Ventas de este mes por sucursal')..."
          [(ngModel)]="prompt"
          (keydown.enter)="consultar()"
        />

        <button
          type="button"
          class="btn-microfono"
          [class.grabando]="grabando()"
          (click)="alternarMicrofono()"
          [title]="grabando() ? 'Detener dictado por voz' : 'Dictar consulta por voz'"
        >
          {{ grabando() ? '🛑 Escuchando...' : '🎙️ Dictar por voz' }}
        </button>

        <button
          type="button"
          class="btn rosa"
          (click)="consultar()"
          [disabled]="generando() || !prompt.trim()"
        >
          {{ generando() ? 'Analizando...' : '✨ Generar Reporte' }}
        </button>
      </div>

      <!-- Sugerencias rápidas -->
      <div class="sugerencias-fila">
        <span class="sugerencias-label">Sugerencias rápidas:</span>
        <button type="button" class="chip-sug" (click)="usarSugerencia('Ventas consolidadas por sucursal')">
          🏢 Ventas por sucursal
        </button>
        <button type="button" class="chip-sug" (click)="usarSugerencia('Top 10 prendas más vendidas del catálogo')">
          ⭐ Top 10 prendas más vendidas
        </button>
        <button type="button" class="chip-sug" (click)="usarSugerencia('Distribución de ventas por canal comercial')">
          💳 Ventas por canal
        </button>
        <button type="button" class="chip-sug" (click)="usarSugerencia('Reporte de existencias e inventario')">
          📦 Stock e inventario
        </button>
      </div>
    </div>

    <!-- 2. BLOQUE DE PLAN BÁSICO (SI ESTÁ BLOQUEADO) -->
    @if (bloqueadoPorPlan()) {
      <div class="tarjeta-upgrade">
        <div class="upgrade-icono">🔒</div>
        <h2>Función Exclusiva del Plan Profesional</h2>
        <p>
          Tu empresa está suscrita al <b>Plan Básico</b>. La generación de reportes con Inteligencia Artificial,
          el dictado por voz y las exportaciones avanzadas son exclusivos del <b>Plan Profesional</b>.
        </p>
        <div class="acciones-upgrade">
          <a class="btn rosa" routerLink="/admin/suscripcion">Ver y Mejorar Mi Plan (CU-05)</a>
        </div>
      </div>
    }

    <!-- 3. RESULTADO DEL REPORTE GENERADO -->
    @if (generando()) {
      <div class="mensaje cargando-ia">
        <div class="spinner-ia">✨</div>
        <b>Orquestando con el modelo de IA y consolidando datos de la empresa...</b>
        <span>Analizando métricas comerciales y generando gráfico de presentación</span>
      </div>
    } @else if (error()) {
      <div class="mensaje error">{{ error() }}</div>
    } @else if (reporte(); as rep) {
      <div class="bloque-reporte">
        <div class="reporte-cabecera">
          <div>
            <h2>{{ rep.titulo }}</h2>
            <span class="reporte-meta">
              Consulta: <i>"{{ rep.consulta_original }}"</i> · Generado el {{ rep.fecha_generacion }}
            </span>
          </div>

          <div class="botones-exportar">
            <button type="button" class="btn linea btn-exp" (click)="exportarExcel()" [disabled]="exportando()">
              📊 Descargar Excel (.xlsx)
            </button>
            <button type="button" class="btn linea btn-exp" (click)="exportarPdf()" [disabled]="exportando()">
              📄 Descargar PDF
            </button>
          </div>
        </div>

        <!-- Síntesis ejecutiva narrativa de la IA -->
        <div class="sintesis-ia">
          <div class="sintesis-tag">💡 Síntesis Ejecutiva (IA)</div>
          <p>{{ rep.resumen_narrativo }}</p>
        </div>

        <!-- Gráfico dinámico SVG sugerido -->
        @if (rep.datos_grafico && rep.datos_grafico.length > 0) {
          <div class="contenedor-grafico-ia">
            <div class="grafico-titulo">Visualización Gráfica Dinámica ({{ rep.tipo_grafico | uppercase }})</div>
            <div class="barras-flex">
              @for (item of rep.datos_grafico; track item.etiqueta) {
                <div class="barra-item">
                  <div class="barra-columna-wrap">
                    <div
                      class="barra-columna"
                      [style.height.%]="calcularPorcentaje(item.valor, rep.datos_grafico)"
                    >
                      <span class="barra-tooltip">Bs {{ moneda(item.valor) }}</span>
                    </div>
                  </div>
                  <span class="barra-etiqueta" [title]="item.etiqueta">{{ item.etiqueta }}</span>
                  <b class="barra-valor">{{ moneda(item.valor) }}</b>
                </div>
              }
            </div>
          </div>
        }

        <!-- Tabla interactiva de datos -->
        <div class="marco-tabla tabla-ia">
          <table>
            <thead>
              <tr>
                @for (col of rep.columnas; track col) {
                  <th>{{ col }}</th>
                }
              </tr>
            </thead>
            <tbody>
              @for (fila of rep.filas; track $index) {
                <tr>
                  @for (col of rep.columnas; track col) {
                    <td>
                      @if (esMoneda(col, fila[col])) {
                        <b>Bs {{ moneda(fila[col]) }}</b>
                      } @else {
                        {{ fila[col] }}
                      }
                    </td>
                  }
                </tr>
              }
            </tbody>
          </table>
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
      max-width: 680px;
      line-height: 1.5;
    }
    .badge-plan-prof {
      background: var(--ganga-suave);
      color: var(--ganga);
      border: 1px solid var(--ganga-borde);
      border-radius: 999px;
      padding: 4px 14px;
      font-size: 11.5px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .bloque-consulta {
      background: #ffffff;
      border: 1px solid var(--linea);
      border-radius: 14px;
      padding: 20px 24px;
      margin-bottom: 24px;
      box-shadow: var(--sombra-sm);
    }
    .barra-input-voz {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }
    .input-prompt {
      flex: 1;
      min-width: 280px;
      font-size: 13.5px;
      padding: 10px 14px;
    }
    .btn-microfono {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #f8fafc;
      border: 1px solid var(--linea);
      border-radius: 8px;
      padding: 9px 15px;
      font-family: inherit;
      font-size: 13px;
      font-weight: 600;
      color: var(--tinta);
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .btn-microfono:hover {
      background: #f1f5f9;
      border-color: var(--linea-fuerte);
    }
    .btn-microfono.grabando {
      background: #fee2e2;
      color: #b91c1c;
      border-color: #fca5a5;
      animation: pulso 1.2s infinite;
    }
    @keyframes pulso {
      0% { opacity: 1; }
      50% { opacity: 0.6; }
      100% { opacity: 1; }
    }
    .sugerencias-fila {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .sugerencias-label {
      font-size: 11.5px;
      color: var(--gris);
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .chip-sug {
      background: var(--papel);
      border: 1px solid var(--linea);
      border-radius: 999px;
      padding: 4px 12px;
      font-size: 11.5px;
      color: var(--tinta);
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .chip-sug:hover {
      border-color: var(--ganga);
      color: var(--ganga);
      background: var(--ganga-suave);
    }
    .tarjeta-upgrade {
      background: #ffffff;
      border: 2px dashed #f59e0b;
      border-radius: 16px;
      padding: 40px 24px;
      text-align: center;
      max-width: 600px;
      margin: 30px auto;
    }
    .upgrade-icono {
      font-size: 40px;
      margin-bottom: 12px;
    }
    .tarjeta-upgrade h2 {
      font-size: 20px;
      font-weight: 800;
      color: var(--tinta);
      margin-bottom: 8px;
    }
    .tarjeta-upgrade p {
      font-size: 13px;
      color: var(--gris);
      line-height: 1.5;
      margin-bottom: 20px;
    }
    .cargando-ia {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;
      padding: 50px 20px;
      background: #ffffff;
      border-radius: 14px;
      border: 1px solid var(--linea);
    }
    .spinner-ia {
      font-size: 32px;
      animation: girar 2s linear infinite;
    }
    @keyframes girar {
      0% { transform: scale(0.9); }
      50% { transform: scale(1.15); }
      100% { transform: scale(0.9); }
    }
    .bloque-reporte {
      background: #ffffff;
      border: 1px solid var(--linea);
      border-radius: 16px;
      padding: 26px 30px;
      box-shadow: var(--sombra-sm);
    }
    .reporte-cabecera {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 18px;
      gap: 16px;
      flex-wrap: wrap;
    }
    .reporte-cabecera h2 {
      font-size: 20px;
      font-weight: 800;
      color: var(--tinta);
      margin: 0 0 4px;
    }
    .reporte-meta {
      font-size: 12px;
      color: var(--gris);
    }
    .botones-exportar {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .btn-exp {
      font-size: 12px;
      padding: 6px 12px;
    }
    .sintesis-ia {
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      border-left: 4px solid var(--ok);
      border-radius: 10px;
      padding: 14px 18px;
      margin-bottom: 22px;
    }
    .sintesis-tag {
      font-size: 11px;
      font-weight: 800;
      color: var(--ok);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 4px;
    }
    .sintesis-ia p {
      margin: 0;
      font-size: 13.5px;
      color: #14532d;
      line-height: 1.5;
    }
    .contenedor-grafico-ia {
      margin-bottom: 26px;
      padding: 18px 20px;
      background: #f8fafc;
      border: 1px solid var(--linea);
      border-radius: 12px;
    }
    .grafico-titulo {
      font-size: 11px;
      font-weight: 700;
      color: var(--gris);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 16px;
    }
    .barras-flex {
      display: flex;
      align-items: flex-end;
      gap: 18px;
      height: 180px;
      padding-bottom: 8px;
      overflow-x: auto;
    }
    .barra-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
      min-width: 70px;
      flex: 1;
      height: 100%;
    }
    .barra-columna-wrap {
      width: 100%;
      height: 120px;
      display: flex;
      align-items: flex-end;
      justify-content: center;
    }
    .barra-columna {
      width: 32px;
      background: var(--ganga);
      border-radius: 6px 6px 0 0;
      transition: height 0.3s ease;
      position: relative;
    }
    .barra-columna:hover {
      background: var(--ganga-hover);
    }
    .barra-etiqueta {
      font-size: 10.5px;
      color: var(--gris);
      text-align: center;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 80px;
    }
    .barra-valor {
      font-size: 11px;
      color: var(--tinta);
    }
    .tabla-ia {
      margin-top: 10px;
    }
  `,
})
export class ReporteGenerativoComponent implements OnInit {
  private http = inject(HttpClient);
  private avisos = inject(Notificaciones);
  readonly sesion = inject(SesionStore);
  readonly moneda = moneda;

  prompt = '';
  readonly reporte = signal<ReporteGenerado | null>(null);
  readonly generando = signal(false);
  readonly exportando = signal(false);
  readonly grabando = signal(false);
  readonly bloqueadoPorPlan = signal(false);
  readonly error = signal<string | null>(null);

  private recognition: any = null;

  ngOnInit(): void {
    this.iniciarReconocimientoVoz();
  }

  usarSugerencia(texto: string): void {
    this.prompt = texto;
    this.consultar();
  }

  consultar(): void {
    const q = this.prompt.trim();
    if (!q) return;

    this.generando.set(true);
    this.error.set(null);
    this.bloqueadoPorPlan.set(false);

    this.http.post<ReporteGenerado>(`${API_URL}/ia/reportes-generativos`, { prompt: q }).subscribe({
      next: (rep) => {
        this.reporte.set(rep);
        this.generando.set(false);
      },
      error: (err) => {
        this.generando.set(false);
        if (err.status === 403 && /Plan Básico/i.test(err.error?.detail ?? '')) {
          this.bloqueadoPorPlan.set(true);
        } else {
          this.error.set(err.error?.detail ?? 'No se pudo generar el reporte.');
        }
      },
    });
  }

  // ------------------------------------------------------------- Dictado por Voz (Web Speech API)
  private iniciarReconocimientoVoz(): void {
    if (typeof window !== 'undefined') {
      const Speech = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (Speech) {
        this.recognition = new Speech();
        this.recognition.lang = 'es-BO';
        this.recognition.continuous = false;
        this.recognition.interimResults = false;

        this.recognition.onresult = (evento: any) => {
          const transcript = evento.results[0][0].transcript;
          this.prompt = transcript;
          this.grabando.set(false);
          this.avisos.ok(`🎙️ Voz reconocida: "${transcript}"`);
          this.consultar();
        };

        this.recognition.onerror = () => {
          this.grabando.set(false);
          this.avisos.error('No se pudo captar el audio o el micrófono fue bloqueado.');
        };

        this.recognition.onend = () => {
          this.grabando.set(false);
        };
      }
    }
  }

  alternarMicrofono(): void {
    if (!this.recognition) {
      this.avisos.error('Tu navegador no soporta Web Speech API. Puedes escribir la consulta por teclado.');
      return;
    }

    if (this.grabando()) {
      this.recognition.stop();
      this.grabando.set(false);
    } else {
      this.grabando.set(true);
      try {
        this.recognition.start();
      } catch {
        this.grabando.set(false);
      }
    }
  }

  // ------------------------------------------------------------- Exportación
  exportarExcel(): void {
    const rep = this.reporte();
    if (!rep) return;
    this.exportando.set(true);

    this.http.post(`${API_URL}/ia/reportes-generativos/exportar-excel`, { reporte: rep }, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        this.descargarArchivo(blob, `reporte_ia_${new Date().toISOString().substring(0, 10)}.xlsx`);
        this.exportando.set(false);
        this.avisos.ok('✓ Reporte exportado a Excel (.xlsx) con éxito.');
      },
      error: () => {
        this.exportando.set(false);
        this.avisos.error('Error al exportar el archivo Excel.');
      },
    });
  }

  exportarPdf(): void {
    const rep = this.reporte();
    if (!rep) return;
    this.exportando.set(true);

    this.http.post(`${API_URL}/ia/reportes-generativos/exportar-pdf`, { reporte: rep }, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        this.descargarArchivo(blob, `reporte_ia_${new Date().toISOString().substring(0, 10)}.pdf`);
        this.exportando.set(false);
        this.avisos.ok('✓ Reporte exportado a PDF con éxito.');
      },
      error: () => {
        this.exportando.set(false);
        this.avisos.error('Error al exportar el documento PDF.');
      },
    });
  }

  private descargarArchivo(blob: Blob, nombre: string): void {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = nombre;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  // ------------------------------------------------------------- Ayudas visuales
  calcularPorcentaje(valor: number, lista: Array<{ valor: number }>): number {
    const maxVal = Math.max(...lista.map((i) => i.valor), 1);
    return Math.max(12, Math.round((valor / maxVal) * 100));
  }

  esMoneda(col: string, val: any): boolean {
    return (
      typeof val === 'number' &&
      (col.includes('(Bs)') || col.includes('Facturado') || col.includes('Importe') || col.includes('Total'))
    );
  }
}
