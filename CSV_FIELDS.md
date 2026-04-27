# Documentación de los campos en los CSV

Este repositorio genera y usa tres archivos CSV principales:
- `resultados_summary.csv`
- `resultados_solution_events.csv`
- `resultados_heuristics.csv`

A continuación se describen los campos de cada uno.

## 1. resultados_summary.csv
Cada fila representa el resultado final de una ejecución de SCIP sobre un problema.

Campos:
- `filename`: nombre del archivo de log original generado por SCIP.
- `problem`: identificador del problema sin el sufijo de archivo ni el modo.
- `mode`: modo de ejecución de SCIP (por ejemplo `agresivo`, `default`, `sin_heuristicas`).
- `gap_target`: brecha objetivo usada en la ejecución (por ejemplo `10.0` para 10%). Puede ser nulo si no se definió.
- `status`: estado final del solucionador (`optimal`, `gap_limit`, `time_limit`, `infeasible`, `unknown`, etc.).
- `solving_time_s`: tiempo de resolución en segundos.
- `total_time_s`: tiempo total transcurrido en segundos (incluye etapas del solucionador adicionales).
- `nodes`: número de nodos explorados hasta el final.
- `nodes_total`: número total de nodos procesados incluyendo aquellos fuera de la rama principal.
- `n_solutions`: cantidad de soluciones factibles encontradas.
- `primal_bound`: cota primal final del problema.
- `dual_bound`: cota dual final del problema.
- `gap_final_pct`: brecha final en porcentaje entre primal y dual.
- `first_sol_value`: valor objetivo de la primera solución encontrada.
- `first_sol_time_s`: tiempo en segundos en que se encontró la primera solución.
- `first_sol_node`: nodo en el que se encontró la primera solución.
- `first_sol_gap_pct`: brecha en porcentaje al momento de la primera solución.
- `first_sol_heuristic`: heurística que generó la primera solución.
- `best_sol_value`: valor objetivo de la mejor solución final.
- `best_sol_time_s`: tiempo en segundos en que se encontró la mejor solución.
- `best_sol_heuristic`: heurística que generó la mejor solución final.
- `gap_last_sol_pct`: brecha en porcentaje de la última solución registrada.
- `time_to_gap_target_s`: tiempo en segundos hasta alcanzar el `gap_target`, si se logró.

## 2. resultados_solution_events.csv
Cada fila describe un evento de mejora de solución en el árbol de B&B durante la ejecución.

Campos:
- `problem`: nombre del problema (igual que en `resultados_summary.csv`).
- `mode`: modo de ejecución.
- `gap_target`: brecha objetivo usada en la ejecución.
- `event_idx`: índice del evento dentro de la secuencia de mejoras.
- `time_s`: tiempo en segundos en el que ocurrió el evento.
- `node`: nodo del árbol de búsqueda donde se registró el evento.
- `primal`: cota primal en ese momento.
- `dual`: cota dual en ese momento.
- `gap_pct`: brecha en porcentaje entre las cotas primal y dual en el evento.
- `source`: origen de la mejora (`heurística`, `LP`, `relaxation`, etc.).
- `source_type`: tipo de origen, normalmente `heuristic`, `lp` o `relaxation`.

## 3. resultados_heuristics.csv
Cada fila contiene estadísticas de una heurística primal usada por SCIP durante la ejecución.

Campos:
- `problem`: nombre del problema.
- `mode`: modo de ejecución.
- `gap_target`: brecha objetivo usada.
- `heuristic`: nombre de la heurística primal.
- `exec_time_s`: tiempo de ejecución total de la heurística en segundos.
- `setup_time_s`: tiempo de preparación de la heurística en segundos.
- `calls`: número de veces que fue llamada la heurística.
- `found`: cantidad de soluciones encontradas por la heurística.
- `best`: número de veces que la heurística produjo la mejor solución del momento.

## Notas adicionales
- El campo `problem` se construye a partir del nombre del log y puede incluir el nombre del problema y el modo.
- El campo `mode` se extrae explícitamente del nombre del log usando convenciones como `agresivo`, `default` y `sin_heuristicas`.
- El campo `gap_target` se interpreta como porcentaje y puede ser `None` si no hubo límite de gap.
