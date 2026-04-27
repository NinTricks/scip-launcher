import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 1. NÚCLEO DE DATOS
# ==========================================
class MIPExperiment:
    """
    Clase central que gestiona la carga y preprocesamiento de los CSV.
    """
    def __init__(self, summary_path, events_path, heuristics_path):
        self.summary = pd.read_csv(summary_path)
        self.events = pd.read_csv(events_path)
        self.heuristics = pd.read_csv(heuristics_path)
        self._preprocess()

    def _preprocess(self):
        """
        Estandariza el nombre de la columna de modo en todos los DataFrames.
        Los CSVs usan 'mode' como nombre de columna; internamente usamos 'modo'.
        """
        for df in [self.summary, self.events, self.heuristics]:
            if 'mode' in df.columns:
                df.rename(columns={'mode': 'modo'}, inplace=True)
    
    def _parse_problem_mode(self, problem_str):
        """
        Parsea el problema y modo de una cadena como '30n20b8_sin_heuristicas'.
        """
        KNOWN_MODES = ['sin_heuristicas', 'agresivo', 'default', 'inteligente']
        for mode in sorted(KNOWN_MODES, key=len, reverse=True):
            suffix = f'_{mode}'
            if problem_str.endswith(suffix):
                instance = problem_str[:-len(suffix)]
                return pd.Series([instance, mode])
        # Fallback: dividir por el último '_'
        parts = problem_str.rsplit('_', 1)
        if len(parts) == 2:
            return pd.Series(parts)
        else:
            return pd.Series([problem_str, 'unknown'])


# ==========================================
# 2. MÓDULOS DE ANÁLISIS (NUEVOS CÁLCULOS)
# ==========================================

def calc_tiempos_resolucion(experiment: MIPExperiment):
    """
    Calcula el tiempo medio, mediano y máximo de resolución por modo.
    Excluye los casos que terminaron en estado `infeasible` o `time_limit`.
    """
    df = experiment.summary
    excluded_count = df['status'].isin(['infeasible', 'time_limit']).sum()
    df = df[~df['status'].isin(['infeasible', 'time_limit'])]
    resumen = df.groupby('modo')['solving_time_s'].agg(
        Media='mean', 
        Mediana='median', 
        DesvEstandar='std',
        Maximo='max'
    ).round(2)
    resumen.attrs['excluded_cases'] = int(excluded_count)
    return resumen

def calc_tiempos_primera_solucion(experiment: MIPExperiment):
    """
    Calcula el tiempo medio, mediano y máximo hasta la primera solución por modo.
    Excluye únicamente los casos que no encontraron ninguna solución
    (first_sol_time_s nulo), independientemente del estado final.
    """
    df = experiment.summary
    excluded_count = df['first_sol_time_s'].isna().sum()
    df = df[df['first_sol_time_s'].notna()]
    resumen = df.groupby('modo')['first_sol_time_s'].agg(
        Media='mean', 
        Mediana='median', 
        DesvEstandar='std',
        Maximo='max'
    ).round(2)
    resumen.attrs['excluded_cases'] = int(excluded_count)
    return resumen


#sugerencia, quitar de TODOS los modos los problemas que no tiren en alguno
#excluir el sin heuristicas tal vez
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

def calc_gap_primera_solucion(experiment: MIPExperiment):
    """
    Calcula la distribución del gap de la primera solución por modo.
    Excluye casos sin primera solución (first_sol_gap_pct nulo).
    Los infinitos se excluyen de la gráfica y tabla pero se reportan aparte.
    """
    df = experiment.summary
    excluded_nulos = df['first_sol_gap_pct'].isna().sum()
    df = df[df['first_sol_gap_pct'].notna()].copy()

    n_infinitos = np.isinf(df['first_sol_gap_pct']).sum()
    df_finito = df[np.isfinite(df['first_sol_gap_pct'])]

    # --- Tabla de percentiles ---
    percentiles = [10, 25, 50, 75, 90, 95]
    print("--- GAP PRIMERA SOLUCIÓN — PERCENTILES (%) ---")
    print(f"{'modo':<20} {'n':>4} {'inf':>4} " + " ".join(f"{'p'+str(p):>8}" for p in percentiles) + f"{'max':>12}")
    print("-" * (20 + 4 + 4 + len(percentiles) * 9 + 13))
    for modo, g in df_finito.groupby('modo'):
        vals = g['first_sol_gap_pct']
        n_inf_modo = np.isinf(df[df['modo'] == modo]['first_sol_gap_pct']).sum()
        pcts = np.percentile(vals, percentiles)
        print(f"{modo:<20} {len(vals):>4} {n_inf_modo:>4} " + " ".join(f"{p:>8.1f}" for p in pcts) + f"{vals.max():>12.1f}")

    print(f"\n(Excluidos por sin primera solución: {excluded_nulos} | Infinitos excluidos de estadísticas: {n_infinitos})")

    # --- Gráfica: boxplot en escala log con los datos finitos ---
    modos = sorted(df_finito['modo'].unique())
    colores = {
        'agresivo':       '#378ADD',
        'default':        '#1D9E75',
        'inteligente':    '#D4537E',
        'sin_heuristicas':'#BA7517',
    }

    datos = [df_finito[df_finito['modo'] == m]['first_sol_gap_pct'].values for m in modos]

    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    bp = ax.boxplot(
        datos,
        patch_artist=True,
        notch=False,
        vert=True,
        widths=0.5,
        showfliers=True,
        flierprops=dict(marker='o', markersize=3, alpha=0.4, linestyle='none'),
        medianprops=dict(linewidth=2, color='white'),
        whiskerprops=dict(linewidth=1),
        capprops=dict(linewidth=1),
    )

    for patch, modo in zip(bp['boxes'], modos):
        c = colores.get(modo, '#888')
        patch.set_facecolor(c)
        patch.set_alpha(0.85)

    for flier, modo in zip(bp['fliers'], modos):
        flier.set_markerfacecolor(colores.get(modo, '#888'))
        flier.set_markeredgecolor(colores.get(modo, '#888'))

    ax.set_yscale('log')
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:,.0f}%'))
    ax.set_xticks(range(1, len(modos) + 1))
    ax.set_xticklabels(modos, fontsize=11)
    ax.set_ylabel('gap primera solución (%)', fontsize=11)
    ax.set_title('distribución del gap de la primera solución por modo', fontsize=12, fontweight='normal')
    ax.grid(axis='y', linestyle='--', linewidth=0.5, alpha=0.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig('gap_primera_solucion.png', dpi=150, bbox_inches='tight')
    plt.show()
    print("Gráfica guardada en 'gap_primera_solucion.png'")

    resumen = df.groupby('modo')['first_sol_gap_pct'].agg(
        Media='mean',
        Mediana='median',
        DesvEstandar='std',
        Maximo='max'
    ).round(2)
    resumen.attrs['excluded_cases'] = int(excluded_nulos)
    return resumen

# ==========================================
# 3. EJECUCIÓN PRINCIPAL
# ==========================================
if __name__ == "__main__":
    # 1. Inicializar el experimento con tus archivos
    # (Asegúrate de que los archivos estén en la misma carpeta o pon la ruta completa)
    experimento = MIPExperiment(
        summary_path='resultados_summary.csv',
        events_path='resultados_solution_events.csv',
        heuristics_path='resultados_heuristics.csv'
    )

    # 2. Ejecutar los módulos de análisis que necesites
    print("--- TIEMPOS DE RESOLUCIÓN POR MODO ---")
    tiempos = calc_tiempos_resolucion(experimento)
    print(tiempos)
    excluded = tiempos.attrs.get('excluded_cases', 0)
    print(f"(Casos excluidos por estado 'infeasible' o 'time_limit': {excluded})")
    print("\n")

    print("--- TIEMPOS HASTA PRIMERA SOLUCIÓN POR MODO ---")
    tiempos_primera = calc_tiempos_primera_solucion(experimento)
    print(tiempos_primera)
    excluded_primera = tiempos_primera.attrs.get('excluded_cases', 0)
    print(f"(Casos excluidos por no tener primera solución: {excluded_primera})")
    print("\n")

    print("--- GAPS PRIMERA SOLUCIÓN ---")
    gaps = calc_gap_primera_solucion(experimento)
    print(gaps)
    excluded = gaps.attrs.get('excluded_cases',0)
    print(f"(Casos excluidos por no tener primera solución con gap: {excluded})")
    print("\n")
