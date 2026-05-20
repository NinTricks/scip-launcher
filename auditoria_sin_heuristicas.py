# Archivo para evaluar cuántos problemas no encontraron
# solución en el modo sin heurísticas al llegar al timeout.

import pandas as pd

df_summary = pd.read_csv("resultados_summary.csv")

sin_heur_tl = df_summary[
(df_summary['mode'] == 'sin_heuristicas') &
(df_summary['status'] == 'time_limit')
]

con_solución = sin_heur_tl[sin_heur_tl['n_solutions'] > 0]
sin_solución = sin_heur_tl[sin_heur_tl['n_solutions'] == 0]
print(f"=== AUDITORÍA 'SIN HEURÍSTICAS' POR TIMEOUT ===")
print(f"Total de instancias en timeout sin heurísticas: {len(sin_heur_tl)}")
print(f"Instancias que SÍ hallaron soluciones válidas: {len(con_solución)}")
print(f"Instancias que NO hallaron ninguna solución: {len(sin_solución)}")

if len(sin_solución) > 0:
    print("\nInstancias críticas sin ninguna solución (Primal Bound Infinito):")
    print(sin_solución[['instance', 'primal_bound', 'dual_bound']].to_string(index=False))