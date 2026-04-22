"""
Programa de análisis automatizado de resultados de benchmark SCIP.

Lee los archivos CSV generados por parser.py y realiza análisis estadísticos
y comparativos de los diferentes modos de configuración de heurísticas.

Uso:
    python analisis.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import os

# Archivos de datos
SUMMARY_CSV = 'resultados_summary.csv'
HEURISTICS_CSV = 'resultados_heuristics.csv'
SOLUTION_EVENTS_CSV = 'resultados_solution_events.csv'

def cargar_datos():
    """Carga los datos de los archivos CSV."""
    if not os.path.exists(SUMMARY_CSV):
        print(f"Error: No se encuentra {SUMMARY_CSV}")
        return None, None, None
    
    summary = pd.read_csv(SUMMARY_CSV)
    heuristics = pd.read_csv(HEURISTICS_CSV) if os.path.exists(HEURISTICS_CSV) else None
    solution_events = pd.read_csv(SOLUTION_EVENTS_CSV) if os.path.exists(SOLUTION_EVENTS_CSV) else None
    
    return summary, heuristics, solution_events

def analizar_summary(summary):
    """Análisis básico del resumen de resultados."""
    print("=== ANÁLISIS DE RESULTADOS SUMMARY ===\n")
    
    # Filtrar solo problemas que encontraron solución
    summary_con_sol = summary[summary['first_sol_time_s'].notna()]
    
    # Estadísticas por modo
    modos = summary_con_sol['mode'].unique()
    print(f"Modos analizados: {', '.join(modos)}")
    print(f"Total problemas con solución encontrada: {len(summary_con_sol)} / {len(summary)}\n")
    
    for modo in modos:
        data_modo = summary_con_sol[summary_con_sol['mode'] == modo]
        print(f"--- Modo: {modo} ---")
        print(f"Número de problemas con solución: {len(data_modo)}")
        print(f"Tiempo promedio de resolución: {data_modo['solving_time_s'].mean():.2f}s")
        print(f"Tiempo promedio a primera solución: {data_modo['first_sol_time_s'].mean():.2f}s")
        print(f"Gap final promedio: {data_modo['gap_final_pct'].mean():.2f}%")
        print(f"Número promedio de soluciones: {data_modo['n_solutions'].mean():.2f}")
        print(f"Número promedio de nodos: {data_modo['nodes'].mean():.0f}")
        print()

def comparar_modos(summary):
    """Compara los modos entre sí."""
    print("=== COMPARACIÓN ENTRE MODOS ===\n")
    
    # Filtrar solo problemas con solución
    summary_con_sol = summary[summary['first_sol_time_s'].notna()]
    
    # Agrupar por modo
    grouped = summary_con_sol.groupby('mode').agg({
        'solving_time_s': ['mean', 'std'],
        'first_sol_time_s': ['mean', 'std'],
        'gap_final_pct': ['mean', 'std'],
        'n_solutions': 'mean',
        'nodes': 'mean'
    }).round(2)
    
    print("Estadísticas por modo (solo problemas con solución encontrada):")
    print(grouped)
    print()

def generar_graficos(summary):
    """Genera gráficos comparativos."""
    print("Generando gráficos...")
    
    # Filtrar solo problemas con solución
    summary_con_sol = summary[summary['first_sol_time_s'].notna()]
    
    # Gráfico de tiempo promedio por modo
    plt.figure(figsize=(10, 6))
    means = summary_con_sol.groupby('mode')['solving_time_s'].mean()
    stds = summary_con_sol.groupby('mode')['solving_time_s'].std()
    plt.bar(means.index, means, yerr=stds, capsize=5, color='skyblue', alpha=0.8)
    plt.title('Tiempo Promedio de Resolución por Modo\n(Solo problemas con solución)')
    plt.ylabel('Tiempo (s)')
    plt.xlabel('Modo')
    plt.xticks(rotation=45)
    plt.ylim(450, 520)  # Zoom para apreciar diferencias
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig('tiempo_por_modo.png')
    plt.close()
    
    # Gráfico de tiempo a primera solución por modo
    plt.figure(figsize=(10, 6))
    means = summary_con_sol.groupby('mode')['first_sol_time_s'].mean()
    stds = summary_con_sol.groupby('mode')['first_sol_time_s'].std()
    plt.bar(means.index, means, yerr=stds, capsize=5, color='lightgreen', alpha=0.8)
    plt.title('Tiempo Promedio a Primera Solución por Modo\n(Solo problemas con solución)')
    plt.ylabel('Tiempo (s)')
    plt.xlabel('Modo')
    plt.xticks(rotation=45)
    plt.ylim(20, 120)  # Zoom para apreciar diferencias
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig('tiempo_primera_solucion.png')
    plt.close()
    
    # Gráfico de gap final promedio por modo
    plt.figure(figsize=(10, 6))
    summary_con_sol.groupby('mode')['gap_final_pct'].mean().plot(kind='bar')
    plt.title('Gap Final Promedio por Modo\n(Solo problemas con solución)')
    plt.ylabel('Gap (%)')
    plt.xlabel('Modo')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('gap_por_modo.png')
    plt.close()
    
    print("Gráficos guardados: tiempo_por_modo.png, tiempo_primera_solucion.png, gap_por_modo.png\n")

def analizar_heuristics(heuristics):
    """Análisis de estadísticas de heurísticas."""
    if heuristics is None:
        print("No se encontraron datos de heurísticas.\n")
        return
    
    print("=== ANÁLISIS DE HEURÍSTICAS ===\n")
    
    # Mejores heurísticas por modo
    for modo in heuristics['mode'].unique():
        data_modo = heuristics[heuristics['mode'] == modo]
        print(f"--- Modo: {modo} ---")
        # Aquí se podría agregar más análisis detallado
        print(f"Número de eventos: {len(data_modo)}")
        print()

def main():
    """Función principal."""
    print("Iniciando análisis de resultados...\n")
    
    # Cargar datos
    summary, heuristics, solution_events = cargar_datos()
    if summary is None:
        return
    
    # Análisis
    analizar_summary(summary)
    comparar_modos(summary)
    generar_graficos(summary)
    analizar_heuristics(heuristics)
    
    print("Análisis completado.")

if __name__ == "__main__":
    main()
