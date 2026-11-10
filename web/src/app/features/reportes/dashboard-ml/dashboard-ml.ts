import { CommonModule, DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { API_URL } from '../../../core/api';
import { Notificaciones } from '../../../core/notificaciones';
import { moneda } from '../../../shared/formato';

export interface MetricaSupervisada {
  nombre: string;
  algoritmo: string;
  r2_score: number;
  rmse: number;
  mae: number;
  fecha_entrenamiento: string;
  muestras: number;
}

export interface MetricaNoSupervisada {
  nombre: string;
  algoritmo: string;
  n_clusters: number;
  silhouette_score: number;
  fecha_entrenamiento: string;
  muestras: number;
}

export interface MetricasML {
  supervisado: MetricaSupervisada;
  no_supervisado: MetricaNoSupervisada;
}

export interface PuntoPrediccion {
  fecha: string;
  semana: number;
  sucursal: string;
  categoria: string;
  ventas_reales: number | null;
  ventas_proyectadas: number;
  limite_inferior: number;
  limite_superior: number;
}

export interface PrediccionesDemanda {
  sucursal: string;
  categoria: string;
  historico: PuntoPrediccion[];
  proyeccion_futura: PuntoPrediccion[];
  resumen_tendencia: string;
  crecimiento_estimado_porcentaje: number;
}

export interface ClusterCliente {
  cluster_id: number;
  etiqueta: string;
  descripcion: string;
  ticket_promedio: number;
  frecuencia_compras: number;
  total_clientes: number;
  porcentaje: number;
  recomendacion_estrategica: string;
}

export interface ClustersResponse {
  total_clientes_analizados: number;
  silhouette_score: number;
  clusters: ClusterCliente[];
}

export interface AlertaQuiebre {
  variante_id: number;
  sku: string;
  prenda: string;
  talla: string;
  color: string;
  sucursal: string;
  stock_actual: number;
  demanda_semanal_estimada: number;
  dias_cobertura_restantes: number;
  nivel_riesgo: string;
  accion_sugerida: string;
}

export interface AlertasResponse {
  total_alertas: number;
  alertas: AlertaQuiebre[];
}

@Component({
  selector: 'app-dashboard-ml',
  standalone: true,
  imports: [CommonModule, FormsModule, DatePipe],
  template: `
    <div class="cabecera-seccion">
      <div>
        <span class="ceja">Hito 3 · Inteligencia Artificial & Analítica</span>
        <h1>Dashboard Analítico de Machine Learning (CU-21)</h1>
        <p class="subtitulo">
          Modelos predictivos de demanda (Random Forest) y segmentación de clientes (K-Means) para toma de decisiones comerciales.
        </p>
      </div>

      <div class="acciones-cabecera">
        <button
          type="button"
          class="btn rosa"
          (click)="reentrenar()"
          [disabled]="entrenando()"
          title="Ejecutar el pipeline de reentrenamiento de modelos en el servidor"
        >
          {{ entrenando() ? 'Reentrenando modelos...' : '🔄 Reentrenar Pipeline ML (CU-20)' }}
        </button>
      </div>
    </div>

    @if (cargando()) {
      <div class="mensaje">Cargando modelos y métricas analíticas...</div>
    } @else if (error()) {
      <div class="mensaje error">{{ error() }}</div>
    } @else {
      <!-- 1. TARJETAS DE CALIDAD ALGORÍTMICA -->
      <div class="metricas-grid">
        <div class="tarjeta-metrica">
          <div class="tarjeta-top">
            <span class="metrica-titulo">Precisión de Demanda (R²)</span>
            <span class="chip-algoritmo">Supervisado</span>
          </div>
          <div class="metrica-valor-grande">
            {{ (metricas()?.supervisado?.r2_score ?? 0) * 100 | number: '1.1-1' }}%
          </div>
          <p class="metrica-desc">
            Algoritmo <b>Random Forest Regressor</b>. RMSE: {{ metricas()?.supervisado?.rmse }} u. · MAE: {{ metricas()?.supervisado?.mae }} u.
          </p>
        </div>

        <div class="tarjeta-metrica">
          <div class="tarjeta-top">
            <span class="metrica-titulo">Cohesión de Clusters (Silhouette)</span>
            <span class="chip-algoritmo no-sup">No Supervisado</span>
          </div>
          <div class="metrica-valor-grande">
            {{ metricas()?.no_supervisado?.silhouette_score ?? 0 | number: '1.2-2' }}
          </div>
          <p class="metrica-desc">
            Algoritmo <b>K-Means (k=3)</b> sobre matriz RFM. Calidad de separación de perfiles óptima (> 0.35).
          </p>
        </div>

        <div class="tarjeta-metrica">
          <div class="tarjeta-top">
            <span class="metrica-titulo">Muestras Entrenadas</span>
            <span class="chip-algoritmo info">Dataset</span>
          </div>
          <div class="metrica-valor-grande">
            {{ metricas()?.supervisado?.muestras }} trans.
          </div>
          <p class="metrica-desc">
            Último entrenamiento: <b>{{ metricas()?.supervisado?.fecha_entrenamiento | date: 'dd/MM/yyyy HH:mm' }}</b>
          </p>
        </div>
      </div>

      <!-- 2. PROYECCIÓN DE DEMANDA FUTURA -->
      <div class="bloque-dashboard">
        <div class="bloque-header">
          <div>
            <h2>Curva de Demanda Proyectada (Próximas 4 semanas)</h2>
            <p class="bloque-sub">Comparativa entre ventas históricas reales y la inferencia predictiva del modelo de regresión.</p>
          </div>

          <div class="selectores-filtro">
            <div class="filtro-campo">
              <label>Sucursal:</label>
              <select class="campo selector" [(ngModel)]="sucursalSeleccionada" (change)="cargarPredicciones()">
                <option value="Sucursal Central">Sucursal Central</option>
                <option value="Sucursal Norte">Sucursal Norte</option>
                <option value="Sucursal Cochabamba">Sucursal Cochabamba</option>
              </select>
            </div>

            <div class="filtro-campo">
              <label>Categoría:</label>
              <select class="campo selector" [(ngModel)]="categoriaSeleccionada" (change)="cargarPredicciones()">
                <option value="Poleras">Poleras</option>
                <option value="Pantalones">Pantalones</option>
                <option value="Camisas">Camisas</option>
                <option value="Vestidos">Vestidos</option>
                <option value="Chamarras">Chamarras</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Banner de interpretación narrativa del modelo -->
        @if (predicciones(); as pred) {
          <div class="banner-tendencia" [class.positivo]="pred.crecimiento_estimado_porcentaje >= 0">
            <span class="tendencia-icono">{{ pred.crecimiento_estimado_porcentaje >= 0 ? '📈' : '📉' }}</span>
            <div class="tendencia-texto">
              <b>Inferencia del Modelo: {{ pred.crecimiento_estimado_porcentaje >= 0 ? 'Tendencia Positiva (+ ' + pred.crecimiento_estimado_porcentaje + '%)' : 'Tendencia a la Baja (' + pred.crecimiento_estimado_porcentaje + '%)' }}</b>
              <p>{{ pred.resumen_tendencia }}</p>
            </div>
          </div>
        }

        <!-- Gráfico SVG Interactivo de la serie temporal -->
        <div class="contenedor-grafico">
          <svg viewBox="0 0 800 240" class="grafico-svg">
            <defs>
              <linearGradient id="gradienteProyeccion" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#059669" stop-opacity="0.25" />
                <stop offset="100%" stop-color="#059669" stop-opacity="0.0" />
              </linearGradient>
            </defs>

            <!-- Líneas de cuadrícula horizontales -->
            <line x1="40" y1="40" x2="780" y2="40" stroke="#e2e8f0" stroke-dasharray="3 3" />
            <line x1="40" y1="100" x2="780" y2="100" stroke="#e2e8f0" stroke-dasharray="3 3" />
            <line x1="40" y1="160" x2="780" y2="160" stroke="#e2e8f0" stroke-dasharray="3 3" />
            <line x1="40" y1="210" x2="780" y2="210" stroke="#cbd5e1" stroke-width="1.5" />

            <!-- Separador vertical entre histórico y futuro -->
            <line x1="533" y1="20" x2="533" y2="210" stroke="#f59e0b" stroke-width="2" stroke-dasharray="4 4" />
            <text x="440" y="32" font-size="10.5" fill="#64748b" font-weight="600">HISTÓRICO REAL</text>
            <text x="545" y="32" font-size="10.5" fill="#059669" font-weight="700">PROYECCIÓN ML (4 SEM)</text>

            <!-- Curva histórica (línea oscura) -->
            <path [attr.d]="svgRutaHistorica()" fill="none" stroke="#0f172a" stroke-width="3" />

            <!-- Puntos históricos -->
            @for (p of puntosHistoricosVisuales(); track p.semana) {
              <circle [attr.cx]="p.x" [attr.cy]="p.y" r="4.5" fill="#0f172a" />
              <text [attr.x]="p.x" y="225" font-size="10" fill="#64748b" text-anchor="middle">S{{ p.semana }}</text>
            }

            <!-- Curva futura (línea punteada esmeralda) -->
            <path [attr.d]="svgRutaFutura()" fill="none" stroke="#059669" stroke-width="3" stroke-dasharray="6 4" />

            <!-- Puntos futuros -->
            @for (p of puntosFuturosVisuales(); track p.semana) {
              <circle [attr.cx]="p.x" [attr.cy]="p.y" r="5" fill="#059669" stroke="#ffffff" stroke-width="2" />
              <text [attr.x]="p.x" [attr.y]="p.y - 10" font-size="10.5" fill="#059669" font-weight="800" text-anchor="middle">
                {{ p.valor }} u.
              </text>
              <text [attr.x]="p.x" y="225" font-size="10" fill="#059669" font-weight="700" text-anchor="middle">S{{ p.semana }}</text>
            }
          </svg>
        </div>
      </div>

      <!-- 3. SEGMENTACIÓN DE CLIENTES (K-MEANS) -->
      <div class="bloque-dashboard">
        <div class="bloque-header">
          <div>
            <h2>Segmentación de Clientes con K-Means (Perfilado RFM)</h2>
            <p class="bloque-sub">Agrupamiento no supervisado según frecuencia de compra y ticket promedio acumulado.</p>
          </div>
          <div class="badge-total-clientes">
            Total analizados: <b>{{ clusters()?.total_clientes_analizados }}</b> clientes
          </div>
        </div>

        <div class="clusters-grid">
          @for (c of clusters()?.clusters; track c.cluster_id) {
            <div class="cluster-tarjeta" [class.vip]="c.etiqueta.includes('VIP')" [class.riesgo]="c.etiqueta.includes('Riesgo')">
              <div class="cluster-cabecera">
                <span class="cluster-icono">{{ c.etiqueta.includes('VIP') ? '👑' : c.etiqueta.includes('Riesgo') ? '⚠️' : '🛍️' }}</span>
                <div>
                  <h3>{{ c.etiqueta }}</h3>
                  <span class="cluster-porcentaje">{{ c.porcentaje }}% de la base ({{ c.total_clientes }} clientes)</span>
                </div>
              </div>

              <div class="cluster-metricas">
                <div class="c-met">
                  <span class="c-met-label">Ticket Promedio</span>
                  <b class="c-met-val">Bs {{ c.ticket_promedio }}</b>
                </div>
                <div class="c-met">
                  <span class="c-met-label">Frecuencia Media</span>
                  <b class="c-met-val">{{ c.frecuencia_compras }} compras/año</b>
                </div>
              </div>

              <p class="cluster-desc">{{ c.descripcion }}</p>

              <div class="cluster-recom">
                <b>Estrategia de Marketing Sugerida:</b>
                <p>{{ c.recomendacion_estrategica }}</p>
              </div>
            </div>
          }
        </div>
      </div>

      <!-- 4. ALERTAS PREDICTIVAS DE QUIEBRE DE STOCK -->
      <div class="bloque-dashboard">
        <div class="bloque-header">
          <div>
            <h2>Alertas Predictivas de Quiebre de Inventario</h2>
            <p class="bloque-sub">Variantes que se agotarán en menos de 15 días según el volumen de ventas proyectado.</p>
          </div>
          <div class="contador-alertas">
            <b>{{ alertas()?.total_alertas }}</b> variantes en riesgo
          </div>
        </div>

        @if ((alertas()?.alertas ?? []).length === 0) {
          <div class="mensaje vacio">
            ✓ Todo el inventario tiene cobertura óptima mayor a 15 días. No hay riesgos inminentes de desabastecimiento.
          </div>
        } @else {
          <div class="marco-tabla">
            <table>
              <thead>
                <tr>
                  <th>Nivel de Riesgo</th>
                  <th>SKU</th>
                  <th>Prenda</th>
                  <th>Talla / Color</th>
                  <th>Sucursal</th>
                  <th>Stock Actual</th>
                  <th>Demanda Proyectada</th>
                  <th>Cobertura Estimada</th>
                  <th>Acción Sugerida</th>
                </tr>
              </thead>
              <tbody>
                @for (alerta of alertas()?.alertas; track alerta.sku) {
                  <tr>
                    <td>
                      <span
                        class="estado"
                        [class.error-badge]="alerta.nivel_riesgo === 'CRITICO'"
                        [class.bajo]="alerta.nivel_riesgo === 'ALTO'"
                        [class.ok]="alerta.nivel_riesgo === 'MODERADO'"
                      >
                        {{ alerta.nivel_riesgo }}
                      </span>
                    </td>
                    <td><span class="mono">{{ alerta.sku }}</span></td>
                    <td><b>{{ alerta.prenda }}</b></td>
                    <td>{{ alerta.talla }} / {{ alerta.color }}</td>
                    <td>{{ alerta.sucursal }}</td>
                    <td>
                      <b>{{ alerta.stock_actual }} u.</b>
                    </td>
                    <td>{{ alerta.demanda_semanal_estimada }} u./sem</td>
                    <td>
                      <span class="cobertura-dias" [class.critico]="alerta.dias_cobertura_restantes <= 4">
                        ~{{ alerta.dias_cobertura_restantes }} días
                      </span>
                    </td>
                    <td>
                      <span class="accion-texto">{{ alerta.accion_sugerida }}</span>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
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
      max-width: 720px;
      line-height: 1.5;
    }
    .metricas-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .tarjeta-metrica {
      background: #ffffff;
      border: 1px solid var(--linea);
      border-radius: 14px;
      padding: 20px 22px;
      box-shadow: var(--sombra-sm);
      display: flex;
      flex-direction: column;
    }
    .tarjeta-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }
    .metrica-titulo {
      font-size: 12.5px;
      font-weight: 700;
      color: var(--gris);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .chip-algoritmo {
      font-size: 10px;
      font-weight: 800;
      padding: 2px 8px;
      border-radius: 999px;
      background: var(--ganga-suave);
      color: var(--ganga);
      border: 1px solid var(--ganga-borde);
    }
    .chip-algoritmo.no-sup {
      background: #eff6ff;
      color: #2563eb;
      border-color: #bfdbfe;
    }
    .chip-algoritmo.info {
      background: #f8fafc;
      color: #64748b;
      border-color: #cbd5e1;
    }
    .metrica-valor-grande {
      font-size: 32px;
      font-weight: 800;
      color: var(--tinta);
      letter-spacing: -0.02em;
      margin-bottom: 6px;
    }
    .metrica-desc {
      font-size: 12px;
      color: var(--gris);
      line-height: 1.4;
      margin: 0;
    }
    .bloque-dashboard {
      background: #ffffff;
      border: 1px solid var(--linea);
      border-radius: 16px;
      padding: 24px 28px;
      margin-bottom: 26px;
      box-shadow: var(--sombra-sm);
    }
    .bloque-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 18px;
      gap: 16px;
      flex-wrap: wrap;
    }
    .bloque-header h2 {
      font-size: 18px;
      font-weight: 800;
      color: var(--tinta);
      letter-spacing: -0.01em;
      margin: 0 0 4px;
    }
    .bloque-sub {
      font-size: 12.5px;
      color: var(--gris);
      margin: 0;
    }
    .selectores-filtro {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    .filtro-campo {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .filtro-campo label {
      font-size: 12px;
      font-weight: 600;
      color: var(--gris);
    }
    .campo.selector {
      padding: 6px 12px;
      font-size: 12.5px;
      width: auto;
    }
    .banner-tendencia {
      display: flex;
      align-items: center;
      gap: 14px;
      background: #f8fafc;
      border: 1px solid var(--linea);
      border-left: 4px solid var(--ganga);
      border-radius: 10px;
      padding: 12px 18px;
      margin-bottom: 18px;
    }
    .banner-tendencia.positivo {
      background: #f0fdf4;
      border-color: #bbf7d0;
      border-left-color: var(--ok);
    }
    .tendencia-icono {
      font-size: 24px;
    }
    .tendencia-texto b {
      display: block;
      font-size: 13.5px;
      color: var(--tinta);
      margin-bottom: 2px;
    }
    .tendencia-texto p {
      margin: 0;
      font-size: 12.5px;
      color: var(--gris);
    }
    .contenedor-grafico {
      width: 100%;
      background: #ffffff;
      border-radius: 8px;
      overflow-x: auto;
    }
    .grafico-svg {
      width: 100%;
      height: auto;
      min-width: 650px;
    }
    .clusters-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 18px;
    }
    .cluster-tarjeta {
      border: 1.5px solid var(--linea);
      border-radius: 12px;
      padding: 20px;
      background: #ffffff;
      display: flex;
      flex-direction: column;
      box-shadow: var(--sombra-sm);
      transition: all 0.2s ease;
    }
    .cluster-tarjeta:hover {
      box-shadow: var(--sombra-md);
      transform: translateY(-2px);
    }
    .cluster-tarjeta.vip {
      border-color: #f59e0b;
      background: #fffdfa;
    }
    .cluster-tarjeta.riesgo {
      border-color: #fca5a5;
      background: #fffcfc;
    }
    .cluster-cabecera {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 14px;
    }
    .cluster-icono {
      font-size: 26px;
    }
    .cluster-cabecera h3 {
      font-size: 15px;
      font-weight: 800;
      color: var(--tinta);
      margin: 0;
    }
    .cluster-porcentaje {
      font-size: 11.5px;
      color: var(--gris);
    }
    .cluster-metricas {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      background: var(--papel);
      padding: 10px 14px;
      border-radius: 8px;
      margin-bottom: 12px;
    }
    .c-met-label {
      display: block;
      font-size: 10.5px;
      color: var(--gris);
      text-transform: uppercase;
    }
    .c-met-val {
      font-size: 13.5px;
      color: var(--tinta);
    }
    .cluster-desc {
      font-size: 12px;
      color: var(--gris);
      line-height: 1.45;
      margin-bottom: 14px;
      flex: 1;
    }
    .cluster-recom {
      background: #f1f5f9;
      border-left: 3px solid var(--ganga);
      padding: 8px 12px;
      border-radius: 4px;
    }
    .cluster-recom b {
      display: block;
      font-size: 11px;
      color: var(--tinta);
      margin-bottom: 2px;
    }
    .cluster-recom p {
      margin: 0;
      font-size: 11.5px;
      color: var(--gris);
      line-height: 1.4;
    }
    .badge-total-clientes, .contador-alertas {
      font-size: 12.5px;
      color: var(--gris);
      background: var(--papel);
      border: 1px solid var(--linea);
      border-radius: 6px;
      padding: 4px 10px;
    }
    .cobertura-dias {
      font-weight: 700;
      color: var(--ok);
    }
    .cobertura-dias.critico {
      color: var(--alerta);
    }
    .error-badge {
      background: #fff1f2;
      color: var(--alerta);
      border: 1px solid #fecdd3;
    }
    .accion-texto {
      font-size: 12px;
      color: var(--gris);
    }
  `,
})
export class DashboardMLComponent implements OnInit {
  private http = inject(HttpClient);
  private avisos = inject(Notificaciones);
  readonly moneda = moneda;

  readonly metricas = signal<MetricasML | null>(null);
  readonly predicciones = signal<PrediccionesDemanda | null>(null);
  readonly clusters = signal<ClustersResponse | null>(null);
  readonly alertas = signal<AlertasResponse | null>(null);

  readonly cargando = signal(true);
  readonly entrenando = signal(false);
  readonly error = signal<string | null>(null);

  sucursalSeleccionada = 'Sucursal Central';
  categoriaSeleccionada = 'Poleras';

  ngOnInit(): void {
    this.cargarTodo();
  }

  cargarTodo(): void {
    this.cargando.set(true);
    this.error.set(null);

    this.http.get<MetricasML>(`${API_URL}/ml/metricas`).subscribe({
      next: (m) => {
        this.metricas.set(m);
        this.cargarPredicciones();
        this.cargarClusters();
        this.cargarAlertas();
        this.cargando.set(false);
      },
      error: () => {
        this.error.set('No se pudieron cargar los modelos de Machine Learning.');
        this.cargando.set(false);
      },
    });
  }

  cargarPredicciones(): void {
    const params = { sucursal: this.sucursalSeleccionada, categoria: this.categoriaSeleccionada };
    this.http.get<PrediccionesDemanda>(`${API_URL}/ml/predicciones`, { params }).subscribe({
      next: (p) => this.predicciones.set(p),
      error: () => {},
    });
  }

  cargarClusters(): void {
    this.http.get<ClustersResponse>(`${API_URL}/ml/clusters`).subscribe({
      next: (c) => this.clusters.set(c),
      error: () => {},
    });
  }

  cargarAlertas(): void {
    this.http.get<AlertasResponse>(`${API_URL}/ml/alertas-quiebre`).subscribe({
      next: (a) => this.alertas.set(a),
      error: () => {},
    });
  }

  reentrenar(): void {
    this.entrenando.set(true);
    this.http.post<any>(`${API_URL}/ml/entrenar`, {}).subscribe({
      next: (res) => {
        this.entrenando.set(false);
        this.metricas.set(res.metricas);
        this.cargarPredicciones();
        this.cargarClusters();
        this.cargarAlertas();
        this.avisos.ok(`✓ Pipeline ML reentrenado con éxito. R²: ${res.metricas.supervisado.r2_score}`);
      },
      error: () => {
        this.entrenando.set(false);
        this.avisos.error('Error al ejecutar el entrenamiento en el servidor.');
      },
    });
  }

  // ------------------------------------------------------------- Cálculos SVG
  puntosHistoricosVisuales(): Array<{ x: number; y: number; semana: number; valor: number }> {
    const hist = this.predicciones()?.historico ?? [];
    if (hist.length === 0) return [];

    const valores = hist.map((p) => p.ventas_reales ?? 0);
    const maxVal = Math.max(...valores, 100);

    return hist.map((p, i) => {
      const x = 60 + i * 58;
      const val = p.ventas_reales ?? 0;
      const y = 200 - (val / maxVal) * 140;
      return { x, y, semana: p.semana, valor: Math.round(val) };
    });
  }

  puntosFuturosVisuales(): Array<{ x: number; y: number; semana: number; valor: number }> {
    const fut = this.predicciones()?.proyeccion_futura ?? [];
    const hist = this.predicciones()?.historico ?? [];
    if (fut.length === 0) return [];

    const valores = [...hist.map((p) => p.ventas_reales ?? 0), ...fut.map((p) => p.ventas_proyectadas)];
    const maxVal = Math.max(...valores, 100);

    const inicioX = 60 + (hist.length - 1) * 58;

    return fut.map((p, i) => {
      const x = inicioX + (i + 1) * 58;
      const val = p.ventas_proyectadas;
      const y = 200 - (val / maxVal) * 140;
      return { x, y, semana: p.semana, valor: Math.round(val) };
    });
  }

  svgRutaHistorica(): string {
    const puntos = this.puntosHistoricosVisuales();
    if (puntos.length === 0) return '';
    return puntos.map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`)).join(' ');
  }

  svgRutaFutura(): string {
    const hist = this.puntosHistoricosVisuales();
    const fut = this.puntosFuturosVisuales();
    if (fut.length === 0) return '';

    const primerPunto = hist.length > 0 ? hist[hist.length - 1] : fut[0];
    let d = `M ${primerPunto.x} ${primerPunto.y}`;
    for (const p of fut) {
      d += ` L ${p.x} ${p.y}`;
    }
    return d;
  }
}
