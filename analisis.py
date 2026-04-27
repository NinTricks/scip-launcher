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


def calc_gap_primera_solucion(experiment: MIPExperiment):
    first_events = experiment.events[experiment.events['event_idx'] == 0][['instance', 'modo', 'gap_pct']]

    total = len(experiment.summary)
    excluded_count = total - len(first_events)

    df = experiment.summary[['instance', 'modo']].merge(first_events, on=['instance', 'modo'], how='inner')

    resumen = df.groupby('modo')['gap_pct'].agg(
        Media='mean',
        Mediana='median',
        DesvEstandar='std',
        Maximo='max'
    ).round(2)
    resumen.attrs['excluded_cases'] = int(excluded_count)

    n_extremos = (df['gap_pct'] > 1000).sum()
    if n_extremos > 0:
        print(f"{n_extremos} caso(s) con gap > 1000% — Considerar mediana en lugar de media.")

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
