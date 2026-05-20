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

############################################################## INTRODUCCIÓN
df_heur = pd.read_csv("resultados_heuristics.csv")
pd.options.display.float_format = '{:.2f}'.format

total_instancias = df_heur['instance'].nunique()
print(f"Dataset cargado con éxito.")
print(f"-> Número total de instancias analizadas: {total_instancias}")
print(f"-> Registros de ejecución de heurísticas: {len(df_heur)}")

print("\n" + "="*40)
print("=== ANÁLISIS INTRODUCTORIO ===")
print("="*40)

analisis_general = df_heur.groupby('mode').agg(
    Tiempo_Ejecucion_S=('exec_time_s', 'sum'),
    Tiempo_Setup_S=('setup_time_s', 'sum'),
    Llamadas_Totales=('calls', 'sum')
).reindex(['sin_heuristicas', 'default', 'agresivo', 'inteligente'])

# tiempo total (exec + setup)
analisis_general['Tiempo_Total_S'] = analisis_general['Tiempo_Ejecucion_S'] + analisis_general['Tiempo_Setup_S']
analisis_general['Tiempo_Total_Horas'] = analisis_general['Tiempo_Total_S'] / 3600

# media por instancia
analisis_general['Tiempo_Medio_por_Instancia_S'] = analisis_general['Tiempo_Total_S'] / total_instancias
analisis_general['Llamadas_Medias_por_Instancia'] = analisis_general['Llamadas_Totales'] / total_instancias

tabla_introduccion = analisis_general[[
    'Tiempo_Total_Horas', 
    'Tiempo_Medio_por_Instancia_S', 
    'Llamadas_Totales', 
    'Llamadas_Medias_por_Instancia'
]]

tabla_introduccion.columns = [
    'Tiempo Total (Horas CPU)', 
    'Tiempo Medio por Instancia (s)', 
    'Llamadas Totales (Volumen)', 
    'Llamadas Medias por Instancia'
]

print(tabla_introduccion)

# gráficos

sns.set_theme(style="whitegrid")
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

colores = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
modos_orden = ['sin_heuristicas', 'default', 'agresivo', 'inteligente']

# tiempo total en horas
sns.barplot(
    ax=axes[0],
    x=tabla_introduccion.index,
    y=tabla_introduccion['Tiempo Total (Horas CPU)'],
    hue=tabla_introduccion.index,
    legend=False,
    palette=colores,
    order=modos_orden
)
axes[0].set_title("Tiempo ejecutando heurísticas", fontsize=12, pad=10)
axes[0].set_ylabel("Tiempo (horas de CPU)", fontsize=11)
axes[0].set_xlabel("Modo de ejecución", fontsize=11)

# llamadas medias por instancia
sns.barplot(
    ax=axes[1],
    x=tabla_introduccion.index,
    y=tabla_introduccion['Llamadas Medias por Instancia'],
    hue=tabla_introduccion.index,
    legend=False,
    palette=colores,
    order=modos_orden
)
axes[1].set_title("Llamadas medias por problema", fontsize=12, pad=10)
axes[1].set_ylabel("Número de llamadas (Promedio)", fontsize=11)
axes[1].set_xlabel("Modo de ejecución", fontsize=11)

plt.suptitle("Análisis del esfuerzo", fontsize=14, y=1.02)
plt.tight_layout()
ruta_foto = os.path.join(CARPETA_GRAFICAS, "introduccion_heuristics.png")
plt.savefig(ruta_foto, dpi=300, bbox_inches='tight')
plt.close()


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
    order=['sin_heuristicas', 'default', 'agresivo', 'inteligente'],
    hue='mode',
    legend=False,
    palette=['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
)

plt.title("Comparativa de Gap Final (%) por Modo\n(Intersección estricta de instancias resueltas)", fontsize=14, pad=15)
plt.ylabel("Gap Final (%)", fontsize=12)
plt.xlabel("Modo de Ejecución", fontsize=12)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.yscale('symlog')
plt.ylim(-0.1, 200)

plt.tight_layout()
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
).reindex(['sin_heuristicas', 'default', 'agresivo', 'inteligente'])

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
).reindex(['sin_heuristicas', 'default', 'agresivo', 'inteligente'])

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
    palette=['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
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
).reindex(['sin_heuristicas', 'default', 'agresivo', 'inteligente'])

tabla_tiempos.insert(2, 'Tasa_Optimos_%', (tabla_tiempos['Optimos_Alcanzados'] / tabla_tiempos['Total_Instancias']) * 100)

tabla_tiempos = tabla_tiempos.drop(columns=['Total_Instancias'])
print(tabla_tiempos.to_string())

plt.figure(figsize=(10, 6))

sns.boxplot(
    x='mode', 
    y='total_time_s', 
    data=df, 
    order=['sin_heuristicas', 'default', 'agresivo', 'inteligente'],
    hue='mode',
    legend=False,
    palette=['#ff9999', '#66b3ff', '#99ff99', '#ffcc99'],
    fliersize=0 # Escondemos los outliers del boxplot para que no se dupliquen con los puntos reales
)

sns.stripplot(
    x='mode', 
    y='total_time_s', 
    data=df, 
    order=['sin_heuristicas', 'default', 'agresivo', 'inteligente'],
    color='.2',      # Color gris oscuro para los puntos
    alpha=0.5,       # Transparencia para detectar nubes o acumulaciones de problemas
    jitter=0.2,      # Dispersión horizontal para que los puntos no se solapen entre sí
    size=4
)

plt.yscale('log')

plt.title("Tiempo de ejecución de cada instancia por modo", fontsize=13, pad=12)
plt.ylabel("Tiempo (segundos) - Escala Log", fontsize=11)
plt.xlabel("Modo de ejecución", fontsize=11)

plt.grid(axis='y', linestyle='--', alpha=0.4, which="both")

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
).reindex(['sin_heuristicas', 'default', 'agresivo', 'inteligente'])

# porcentaje de instancias donde el modo no encontró
tabla_primera.insert(1, '%_Fracaso_Sin_Sol', (tabla_primera['Instancias_Sin_Solucion'] / tabla_primera['Total_Instancias']) * 100)

tabla_primera = tabla_primera.drop(columns=['Total_Instancias'])
print(tabla_primera.to_string())


plt.figure(figsize=(10, 6))
sns.boxplot(
    x='mode', 
    y='first_sol_time_cleaned', 
    data=df_primera, 
    order=['sin_heuristicas', 'default', 'agresivo', 'inteligente'],
    hue='mode',
    legend=False,
    palette=['#ff9999', '#66b3ff', '#99ff99', '#ffcc99'],
    fliersize=0
)

sns.stripplot(
    x='mode', 
    y='first_sol_time_cleaned', 
    data=df_primera, 
    order=['sin_heuristicas', 'default', 'agresivo', 'inteligente'],
    color='.2',
    alpha=0.5,
    jitter=0.2,
    size=4
)

plt.yscale('log')

plt.title("Tiempo hasta la primera solución\n(imputando el tiempo límite a las instancias no resueltas)", fontsize=13, pad=12)
plt.ylabel("Tiempo (segundos) - Escala Log", fontsize=11)
plt.xlabel("Modo de ejecución", fontsize=11)
plt.grid(axis='y', linestyle='--', alpha=0.4, which="both")

ruta_grafica_primera = os.path.join(CARPETA_GRAFICAS, "boxplot_tiempo_primera_solucion.png")
plt.tight_layout()
plt.savefig(ruta_grafica_primera, dpi=300)
plt.close()

