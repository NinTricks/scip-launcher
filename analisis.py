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
        Limpia y estandariza los datos. 
        Extrae la 'instancia' y el 'modo' de la columna 'problem'.
        Ejemplo: '30n20b8_agresivo' -> instancia: '30n20b8', modo: 'agresivo'
        Maneja modos que contienen '_', como 'sin_heuristicas'.
        """
        for df in [self.summary, self.events, self.heuristics]:
            if 'problem' in df.columns:
                df[['instance', 'modo']] = df['problem'].apply(self._parse_problem_mode)
    
    def _parse_problem_mode(self, problem_str):
        """
        Parsea el problema y modo de una cadena como '30n20b8_sin_heuristicas'.
        """
        KNOWN_MODES = ['sin_heuristicas', 'agresivo', 'default', 'fast', 'off', 'inteligente'] #soñador, sobra alguno
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
    Módulo 1: Calcula el tiempo medio, mediano y máximo de resolución por modo.
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
