import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os


def shifted_geometric_mean(series, shift=1.0):
    return np.exp(np.mean(np.log(series + shift))) - shift

CARPETA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
CARPETA_GRAFICAS = os.path.join(CARPETA_SCRIPT, "gráficas")
os.makedirs(CARPETA_GRAFICAS, exist_ok=True)

colores_dict = {
    'sin_heuristicas': '#ff9999',
    'default': '#66b3ff',
    'agresivo': '#99ff99',
    'inteligente': '#ffcc99'
}

modos_orden = ['sin_heuristicas', 'default', 'agresivo', 'inteligente']

############################################################## INTRODUCCIÓN
df_heur = pd.read_csv("resultados_heuristics.csv")
pd.options.display.float_format = '{:.2f}'.format

total_instancias = df_heur['instance'].nunique()
print(f"Dataset cargado con éxito.")
print(f"-> Número total de instancias analizadas: {total_instancias}")
print(f"-> Registros de ejecución de heurísticas: {len(df_heur)}")

############################################################## GAP FINAL GRÁFICA
# cargar los datos y limpiar infinitos
df = pd.read_csv("resultados_summary.csv")
df['gap_final_pct'] = df['gap_final_pct'].replace([np.inf, -np.inf], np.nan)

# Filtrar problemas infactibles o que no encontraron solución
# Eliminamos aquellos con primal_bound infinito o que literalmente sean status = 'infeasible'
df_valid = df[(df['primal_bound'] < 1e19) & (df['status'] != 'infeasible')].copy()


# Contamos en cuántos modos tiene solución cada instancia
conteo_modos = df_valid.groupby('instance')['mode'].nunique()

# Nos quedamos solo con las instancias que tienen solución en los 4 modos
instancias_comunes = conteo_modos[conteo_modos == 4].index
df_fair = df_valid[df_valid['instance'].isin(instancias_comunes)]


plt.figure(figsize=(10, 6))

# Seaborn para pintar el boxplot
sns.boxplot(
    x='mode', 
    y='gap_final_pct', 
    data=df_fair, 
    order=modos_orden,
    hue='mode',
    legend=False,
    palette=colores_dict
)

plt.title("Comparativa de Gap Final (%) por Modo\n(Intersección estricta de instancias resueltas)", fontsize=14, pad=15)
plt.ylabel("Gap Final (%)", fontsize=12)
plt.xlabel("Modo de Ejecución", fontsize=12)
plt.grid(axis='y', linestyle='--', alpha=0.7)
#plt.yscale('symlog')
plt.ylim(0, 5)

#plt.tight_layout()
ruta_foto = os.path.join(CARPETA_GRAFICAS, "boxplot_gap_final.png")
plt.savefig(ruta_foto, dpi=300)
plt.close()


################################################################# GAP FINAL ESTADÍSTICAS
# 2 decimales
pd.options.display.float_format = '{:.2f}'.format

# Resumen
resumen_stats = df_fair.groupby('mode').agg(
    Media_Aritmetica=('gap_final_pct', 'mean'),
    Media_Geometrica=('gap_final_pct', lambda x: shifted_geometric_mean(x, shift=1.0)),
    Mediana=('gap_final_pct', 'median'),
    Desviacion_Estandar=('gap_final_pct', 'std'),
    Maximo=('gap_final_pct', 'max')
).reindex(modos_orden)

resumen_stats.columns = [
    'Media Aritmética', 
    'Media Geométrica (s=1)', 
    'Mediana', 
    'Desviación Estándar', 
    'Máximo'
]

print("\n" + "="*40)
print("=== RESUMEN GAP FINAL (%) ===")
print("="*40)
print(f"Total de instancias usadas para la comparativa justa: {len(instancias_comunes)}")
print(resumen_stats)


################################################################### ANÁLISIS HEURÍSTICAS
print("\n" + "="*40)
print("=== ANÁLISIS DE HEURÍSTICAS ===")
print("="*40)

# cargar datos
df_heur = pd.read_csv("resultados_heuristics.csv")
# no quitamos los malos porque todos los problemas se han esforzado en tirar heurísticas

# sumamos el tiempo de ejecución y configuración por modo
tiempo_modo = df_heur.groupby('mode').agg(
    Tiempo_Ejecucion_S=('exec_time_s', 'sum'),
    Tiempo_Setup_S=('setup_time_s', 'sum'),
    Llamadas_Totales=('calls', 'sum')
).reindex(modos_orden)

# calcular tiempo total (exec + setup)
tiempo_modo['Tiempo_Total_Heur_S'] = tiempo_modo['Tiempo_Ejecucion_S'] + tiempo_modo['Tiempo_Setup_S']
# en horas
tiempo_modo['Tiempo_Total_Heur_Horas'] = tiempo_modo['Tiempo_Total_Heur_S'] / 3600
print(tiempo_modo)

# gráfico
plt.figure(figsize=(9, 5))
sns.barplot(
    x=tiempo_modo.index, 
    y=tiempo_modo['Tiempo_Total_Heur_Horas'], 
    hue=tiempo_modo.index,
    legend=False,
    palette=colores_dict
)
plt.title("Tiempo total invertido en heurísticas", fontsize=13, pad=12)
plt.ylabel("Tiempo total (horas de CPU)", fontsize=11)
plt.xlabel("Modo de ejecución", fontsize=11)
plt.grid(axis='y', linestyle='--', alpha=0.5)
plt.tight_layout()
ruta_foto = os.path.join(CARPETA_GRAFICAS, "tiempo_global_heurísticas_horas.png")
plt.savefig(ruta_foto, dpi=300)
plt.close()

################################################################ TIEMPO POR INSTANCIA
print("\n" + "="*40)
print("=== TIEMPO POR INSTANCIA ===")
print("="*40)

# auxiliares para el pandas
def p25(x): return x.quantile(0.25)
def p75(x): return x.quantile(0.75)
def p90(x): return x.quantile(0.90)

tabla_tiempos = df.groupby('mode').agg(
    Total_Instancias=('instance', 'count'),
    # Contamos cuántas terminaron en óptimo y cuántas agotaron el tiempo
    Optimos_Alcanzados=('status', lambda x: (x == 'optimal').sum()),
    Timeouts=('status', lambda x: (x == 'time_limit').sum()),
    # Distribución del tiempo de ejecución
    Minimo_s=('total_time_s', 'min'),
    Percentil_25_s=('total_time_s', p25),
    Mediana_s=('total_time_s', 'median'),
    Percentil_75_s=('total_time_s', p75),
    Percentil_90_s=('total_time_s', p90)
).reindex(modos_orden)

tabla_tiempos.insert(2, 'Tasa_Optimos_%', (tabla_tiempos['Optimos_Alcanzados'] / tabla_tiempos['Total_Instancias']) * 100)

tabla_tiempos = tabla_tiempos.drop(columns=['Total_Instancias'])
print(tabla_tiempos.to_string())

plt.figure(figsize=(10, 6))

sns.boxplot(
    x='mode', 
    y='total_time_s', 
    data=df, 
    order=modos_orden,
    hue='mode',
    legend=False,
    palette=colores_dict,
    fliersize=0 
)

sns.stripplot(
    x='mode', 
    y='total_time_s', 
    data=df, 
    order=modos_orden,
    color='.2',
    alpha=0.5,
    jitter=0.2,
    size=4
)

plt.yscale('log')

plt.title("Tiempo de ejecución de cada instancia por modo", fontsize=13, pad=12)
plt.ylabel("Tiempo (segundos) - Escala Log", fontsize=11)
plt.xlabel("Modo de ejecución", fontsize=11)

plt.grid(axis='y', linestyle='--', alpha=0.5)

ruta_boxplot_instancias = os.path.join(CARPETA_GRAFICAS, "boxplot_tiempos_instancias.png")
plt.tight_layout()
plt.savefig(ruta_boxplot_instancias, dpi=300)
plt.close()


################################################################### TIEMPO HASTA PRIMERA SOLUCIÓN
print("\n" + "="*40)
print("=== TIEMPO HASTA PRIMERA SOLUCIÓN ===")
print("="*40)

df_primera = df.copy()

# si no ha encontrado solución le ponemos el tiempo límite
df_primera['first_sol_time_cleaned'] = df_primera['first_sol_time_s'].fillna(df_primera['total_time_s'])

tabla_primera = df_primera.groupby('mode').agg(
    Total_Instancias=('instance', 'count'),
    Instancias_Sin_Solucion=('first_sol_time_s', lambda x: x.isna().sum()),
    Minimo_s=('first_sol_time_cleaned', 'min'),
    Percentil_25_s=('first_sol_time_cleaned', p25),
    Mediana_s=('first_sol_time_cleaned', 'median'),
    Percentil_75_s=('first_sol_time_cleaned', p75),
    Percentil_90_s=('first_sol_time_cleaned', p90),
    Maximo_s=('first_sol_time_cleaned', 'max')
).reindex(modos_orden)

# porcentaje de instancias donde el modo no encontró
tabla_primera.insert(1, '%_Fracaso_Sin_Sol', (tabla_primera['Instancias_Sin_Solucion'] / tabla_primera['Total_Instancias']) * 100)

tabla_primera = tabla_primera.drop(columns=['Total_Instancias'])
print(tabla_primera.to_string())


plt.figure(figsize=(10, 6))
sns.boxplot(
    x='mode', 
    y='first_sol_time_cleaned', 
    data=df_primera, 
    order=modos_orden,
    hue='mode',
    legend=False,
    palette=colores_dict,
    fliersize=0
)

sns.stripplot(
    x='mode', 
    y='first_sol_time_cleaned', 
    data=df_primera, 
    order=modos_orden,
    color='.2',
    alpha=0.5,
    jitter=0.2,
    size=4
)

plt.yscale('log')

plt.title("Tiempo hasta la primera solución\n(imputando el tiempo límite a las instancias no resueltas)", fontsize=13, pad=12)
plt.ylabel("Tiempo (segundos) - Escala Log", fontsize=11)
plt.xlabel("Modo de ejecución", fontsize=11)
plt.grid(axis='y', linestyle='--', alpha=0.5)

ruta_grafica_primera = os.path.join(CARPETA_GRAFICAS, "boxplot_tiempo_primera_solucion.png")
plt.tight_layout()
plt.savefig(ruta_grafica_primera, dpi=300)
plt.close()

################################################################### PROPORCIÓN DE TIEMPO EN HEURÍSTICAS
print("\n" + "="*40)
print("=== PROPORCIÓN DE TIEMPO EN HEURÍSTICAS ===")
print("="*40)

df_heur_inst = df_heur.groupby(['instance', 'mode']).agg(
    Tiempo_Heur_S=('exec_time_s', 'sum')  # solo exec, no setup, para ser justo con el solver
).reset_index()

df_merged = df.merge(df_heur_inst, on=['instance', 'mode'], how='left')
df_merged['Tiempo_Heur_S'] = df_merged['Tiempo_Heur_S'].fillna(0)
df_merged['Prop_Heur_Pct'] = (df_merged['Tiempo_Heur_S'] / df_merged['total_time_s']) * 100

tabla_prop_modo = df_merged.groupby('mode').agg(
    Tiempo_Total_Solver_S=('total_time_s', 'sum'),
    Tiempo_Total_Heur_S=('Tiempo_Heur_S', 'sum'),
    Media_Prop_Pct=('Prop_Heur_Pct', 'mean'),
    Mediana_Prop_Pct=('Prop_Heur_Pct', 'median'),
    Max_Prop_Pct=('Prop_Heur_Pct', 'max')
).reindex(modos_orden)

tabla_prop_modo['Prop_Global_Pct'] = (
    tabla_prop_modo['Tiempo_Total_Heur_S'] / tabla_prop_modo['Tiempo_Total_Solver_S']
) * 100

tabla_prop_modo.columns = [
    'Tiempo Total Solver (s)',
    'Tiempo Total Heur (s)',
    'Media Proporción (%)',
    'Mediana Proporción (%)',
    'Máx Proporción (%)',
    'Proporción Global (%)'
]

print("\n-- Proporción global por modo --")
print(tabla_prop_modo.to_string())


plt.figure(figsize=(10, 6))


sns.boxplot(
    x='mode', y='Prop_Heur_Pct', data=df_merged,
    order=modos_orden, hue='mode', legend=False, palette=colores_dict, fliersize=0
)
sns.stripplot(
    x='mode', y='Prop_Heur_Pct', data=df_merged,
    order=modos_orden, color='.2', alpha=0.5, jitter=0.2, size=4
)

plt.title("Proporción del tiempo dedicado a heurísticas por instancia", fontsize=13, pad=12)
plt.ylabel("% del tiempo total del solver", fontsize=11)
plt.xlabel("Modo de ejecución", fontsize=11)
plt.grid(axis='y', linestyle='--', alpha=0.5)

plt.tight_layout()
ruta_foto = os.path.join(CARPETA_GRAFICAS, "proporcion_tiempo_heuristicas.png")
plt.savefig(ruta_foto, dpi=300)
plt.close()


############################################################## TIEMPO POR MODO
print("\n" + "="*40)
print("=== ANÁLISIS DE TIEMPO POR MODO ===")
print("="*40)

# 1. Cargar el dataset principal
df_summary = pd.read_csv("resultados_summary.csv")

# 2. Calcular estadísticas de tiempo (en segundos) agrupando por modo
analisis_tiempo = df_summary.groupby('mode').agg(
    Instancias=('instance', 'count'),
    Tiempo_Total_S=('total_time_s', 'sum'),
    Tiempo_Medio_S=('total_time_s', 'mean'),
    Mediana_Tiempo_S=('total_time_s', 'median'),
    Tiempo_Max_S=('total_time_s', 'max')
).reindex(modos_orden)

# Convertir el tiempo total a horas para dar un dato más legible a nivel global
analisis_tiempo['Tiempo_Total_Horas'] = analisis_tiempo['Tiempo_Total_S'] / 3600

# Formateamos la salida en consola para que sea fácil de leer
print("Estadísticas de tiempo de ejecución del solver por modo:\n")
tabla_imprimir = analisis_tiempo[[
    'Tiempo_Total_Horas', 
    'Tiempo_Medio_S', 
    'Mediana_Tiempo_S', 
    'Tiempo_Max_S'
]].copy()

tabla_imprimir.columns = [
    'Total (Horas)', 
    'Media (s)', 
    'Mediana (s)', 
    'Máximo (s)'
]
print(tabla_imprimir.to_string(float_format="{:.2f}".format))

# 3. Generar la visualización (Gráfico de barras del Tiempo Medio)
plt.figure(figsize=(9, 5))

sns.barplot(
    x=analisis_tiempo.index,
    y=analisis_tiempo['Tiempo_Medio_S'],
    hue=analisis_tiempo.index,
    legend=False,
    palette=colores_dict,
    order=modos_orden
)

plt.title("Tiempo Medio de Ejecución del Solver por Modo", fontsize=14, pad=15)
plt.ylabel("Tiempo Medio (segundos)", fontsize=12)
plt.xlabel("Modo de Ejecución", fontsize=12)
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Guardar la gráfica
ruta_foto_tiempo = os.path.join(CARPETA_GRAFICAS, "tiempo_medio_por_modo.png")
plt.tight_layout()
plt.savefig(ruta_foto_tiempo, dpi=300)
plt.close()

print(f"\n-> Gráfica guardada en: {ruta_foto_tiempo}")