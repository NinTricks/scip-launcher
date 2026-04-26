import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 1. NÚCLEO DE DATOS (NO SE TOCA PARA AÑADIR CÁLCULOS)
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
        """
        for df in [self.summary, self.events, self.heuristics]:
            if 'problem' in df.columns:
                # El parámetro n=1 asegura que solo separe por el último guion bajo
                df[['instance', 'modo']] = df['problem'].str.rsplit('_', n=1, expand=True)


# ==========================================
# 2. MÓDULOS DE ANÁLISIS (AQUÍ AÑADES TUS NUEVOS CÁLCULOS)
# ==========================================

def calc_tiempos_resolucion(experiment: MIPExperiment):
    """
    Módulo 1: Calcula el tiempo medio, mediano y máximo de resolución por modo.
    """
    df = experiment.summary
    resumen = df.groupby('modo')['solving_time_s'].agg(
        Media='mean', 
        Mediana='median', 
        DesvEstandar='std',
        Maximo='max'
    ).round(2)
    return resumen

def calc_ahorro_nodos(experiment: MIPExperiment):
    """
    Módulo 2: Compara la cantidad de nodos explorados entre modos.
    """
    df = experiment.summary
    nodos = df.groupby('modo')['nodes'].agg(['mean', 'median']).round(0)
    return nodos

def calc_roi_heuristicas(experiment: MIPExperiment):
    """
    Módulo 3: Calcula el Retorno de Inversión (ROI) de cada heurística por modo.
    Métrica: Soluciones encontradas por segundo de ejecución.
    """
    df = experiment.heuristics.copy()
    # Reemplazamos 0 por NaN temporalmente para evitar división por cero
    df['exec_time_s_safe'] = df['exec_time_s'].replace(0, np.nan)
    df['sol_per_sec'] = df['found'] / df['exec_time_s_safe']
    
    # Agrupamos para ver qué heurística es más eficiente en cada modo
    roi = df.groupby(['modo', 'heuristic'])['sol_per_sec'].mean().dropna().round(4)
    return roi

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
    print("\n")

    print("--- NODOS EXPLORADOS POR MODO ---")
    nodos = calc_ahorro_nodos(experimento)
    print(nodos)
    print("\n")

    print("--- ROI DE HEURÍSTICAS (Top 5 en modo agresivo) ---")
    roi = calc_roi_heuristicas(experimento)
    if 'agresivo' in roi.index.get_level_values('modo'):
        print(roi['agresivo'].sort_values(ascending=False).head(5))