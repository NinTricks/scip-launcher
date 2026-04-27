"""
Parser de logs SCIP para análisis de benchmark de heurísticas primales.

Convención de nombres de archivo esperada:
    <nombre_problema>_<modo>_resultado.log

Modos soportados: agresivo, default, sin_heuristicas
También soporta ejecuciones con gap objetivo: <nombre>_<modo>_gap<N>_resultado.log
  Ejemplo: unitcal_7_agresivo_gap05_resultado.log  (gap objetivo = 0.5%)

Uso:
    python scip_log_parser.py <directorio_o_lista_de_logs> [--output resultados.csv]
"""

import re
import os
import sys
import json
import csv
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Estructuras de datos
# ---------------------------------------------------------------------------

@dataclass
class SolutionEvent:
    """Una mejora de solución registrada en el árbol B&B."""
    time_s: float
    node: int
    primal: float
    dual: float
    gap_pct: float
    source: str        # heurística o 'LP' / 'relaxation'
    source_type: str   # 'heuristic' | 'lp' | 'relaxation'


@dataclass
class HeuristicStats:
    """Fila de la tabla 'Primal Heuristics' del log."""
    name: str
    exec_time_s: float
    setup_time_s: float
    calls: int
    found: int         # soluciones encontradas
    best: int          # veces que fue la mejor


@dataclass
class SCIPResult:
    """Todo lo extraído de un único log SCIP."""
    # --- identificación ---
    filename: str
    problem: str
    mode: str          # agresivo | default | sin_heuristicas
    gap_target: Optional[float]   # None = sin límite de gap

    # --- estado final ---
    status: str        # 'optimal' | 'gap_limit' | 'time_limit' | 'infeasible' | 'unknown'
    solving_time_s: float
    total_time_s: float
    nodes: int
    nodes_total: int
    n_solutions: int
    primal_bound: float
    dual_bound: float
    gap_final_pct: float

    # --- primera solución ---
    first_sol_value: Optional[float]
    first_sol_time_s: Optional[float]
    first_sol_node: Optional[int]
    first_sol_gap_pct: Optional[float]
    first_sol_heuristic: Optional[str]

    # --- mejor solución ---
    best_sol_value: Optional[float]
    best_sol_time_s: Optional[float]
    best_sol_heuristic: Optional[str]
    gap_last_sol_pct: Optional[float]

    # --- tiempo hasta gap objetivo alcanzado (si aplica) ---
    time_to_gap_target_s: Optional[float]

    # --- secuencia de mejoras ---
    solution_events: list = field(default_factory=list)

    # --- tabla de heurísticas ---
    heuristic_stats: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

# Regex para la línea de mejora en el árbol B&B
# Ejemplo: "d 329s|     1 |     0 |144047 |     - |farkasdi|..."
# Ejemplo: "* 362s|   145 |    47 |176733 | 601.3 |    LP  |..."
RE_BB_SOL = re.compile(
    r'^[dDlLoO*hHbBcCpPrRsSuU]\s+(\d+)s\|\s*(\d+)\s*\|'   # time | node
    r'.*?\|\s*([a-zA-Z0-9 _\-]+?)\s*\|'                   # heur/LP column
    r'.*?\|\s*([\d.e+\-]+)\s*\|\s*([\d.e+\-]+)\s*\|'      # dual | primal
    r'\s*([\d.]+)%'                                         # gap%
)

# Regex tabla Primal Heuristics
RE_HEUR_TABLE = re.compile(
    r'^\s{2}(\w[\w\s]*?)\s*:\s+'
    r'([\d.]+)\s+([\d.]+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$'
)

# Regex líneas de resumen final
RE_STATUS   = re.compile(r'SCIP Status\s*:\s*(.+)')
RE_SOLVE_T  = re.compile(r'Solving Time \(sec\)\s*:\s*([\d.]+)')
RE_TOTAL_T  = re.compile(r'Total Time\s*:\s+([\d.]+)')
RE_NODES    = re.compile(r'Solving Nodes\s*:\s*(\d+)(?:\s*\(total of (\d+) nodes)?')
RE_PRIMAL   = re.compile(r'^Primal Bound\s*:\s*([+\-][\d.e+\-]+)\s*\((\d+) solutions\)')
RE_DUAL     = re.compile(r'^Dual Bound\s*:\s*([+\-][\d.e+\-]+)')
RE_GAP      = re.compile(r'^Gap\s*:\s*([\d.]+)\s*%')
RE_NODES_TOT= re.compile(r'nodes \(total\)\s*:\s*(\d+)')

# Regex sección Solution (final detallada)
RE_SOL_FOUND= re.compile(r'Solutions found\s*:\s*(\d+)')
RE_FIRST_SOL= re.compile(
    r'First Solution\s*:\s*([+\-][\d.e+\-]+)\s*'
    r'\(in run \d+, after (\d+) nodes, ([\d.]+) seconds.*?found by <(.+?)>\)'
)
RE_GAP_FIRST= re.compile(r'Gap First Sol\.\s*:\s*([\d.]+|infinite)\s*%?')
RE_GAP_LAST = re.compile(r'Gap Last Sol\.\s*:\s*([\d.]+|infinite)\s*%?')
RE_BEST_SOL = re.compile(
    r'Primal Bound\s*:\s*([+\-][\d.e+\-]+)\s*'
    r'\(in run \d+, after \d+ nodes, ([\d.]+) seconds.*?found by <(.+?)>\)'
)


def _heuristic_type(name: str) -> str:
    name = name.strip().lower()
    if name in ('lp', 'lp solutions', 'relax solutions', 'pseudo solutions', 'strong branching'):
        return 'lp'
    if name == 'relaxation':
        return 'relaxation'
    return 'heuristic'


def _parse_filename(filename: str):
    """
    Extrae (problem, mode, gap_target) del nombre de archivo.
    Convención: <problem>_<mode>[_gap<N>]_resultado.log
    gap<N> -> N/10 como porcentaje  (gap05 = 0.5%, gap10 = 1.0%)
    """
    stem = Path(filename).stem  # quita .log
    # quitar sufijo _resultado
    stem = re.sub(r'_resultado$', '', stem)

    # detectar gap objetivo opcional — dos formatos:
    #   _gap05  -> 0.5%   (formato legacy)
    #   _10.0   -> 10.0%  (formato float directo)
    gap_target = None
    gap_match = re.search(r'_gap(\d+)', stem)
    if gap_match:
        gap_target = int(gap_match.group(1)) / 10.0
        stem = stem[:gap_match.start()] + stem[gap_match.end():]
    else:
        gap_match = re.search(r'_([\d]+\.[\d]+)$', stem)
        if gap_match:
            gap_target = float(gap_match.group(1))
            stem = stem[:gap_match.start()]

    # Modos conocidos (pueden contener '_')
    KNOWN_MODES = ['sin_heuristicas', 'agresivo', 'default', 'inteligente', 'fast', 'off']
    mode = 'unknown'
    problem = stem
    for km in sorted(KNOWN_MODES, key=len, reverse=True):
        suffix = f'_{km}'
        if stem.endswith(suffix):
            problem = stem[:-len(suffix)]
            mode = km
            break
    if mode == 'unknown':
        parts = stem.rsplit('_', 1)
        if len(parts) == 2:
            problem, mode = parts

    return problem, mode, gap_target


def parse_log(filepath: str) -> SCIPResult:
    filename = os.path.basename(filepath)
    problem, mode, gap_target = _parse_filename(filename)

    result = SCIPResult(
        filename=filename,
        problem=problem,
        mode=mode,
        gap_target=gap_target,
        status='unknown',
        solving_time_s=0.0,
        total_time_s=0.0,
        nodes=0,
        nodes_total=0,
        n_solutions=0,
        primal_bound=float('inf'),
        dual_bound=float('-inf'),
        gap_final_pct=float('inf'),
        first_sol_value=None,
        first_sol_time_s=None,
        first_sol_node=None,
        first_sol_gap_pct=None,
        first_sol_heuristic=None,
        best_sol_value=None,
        best_sol_time_s=None,
        best_sol_heuristic=None,
        gap_last_sol_pct=None,
        time_to_gap_target_s=None,
    )

    in_heur_table = False

    with open(filepath, 'r', errors='replace') as f:
        for line in f:
            line_stripped = line.rstrip('\n')

            # --- tabla heurísticas ---
            if 'Primal Heuristics' in line_stripped and 'ExecTime' in line_stripped:
                in_heur_table = True
                continue
            if in_heur_table:
                if line_stripped.startswith('  ') and ':' in line_stripped:
                    m = RE_HEUR_TABLE.match(line_stripped)
                    if m:
                        result.heuristic_stats.append(HeuristicStats(
                            name=m.group(1).strip(),
                            exec_time_s=float(m.group(2)),
                            setup_time_s=float(m.group(3)),
                            calls=int(m.group(4)),
                            found=int(m.group(5)),
                            best=int(m.group(6)),
                        ))
                    continue
                elif line_stripped.startswith('LNS') or line_stripped.startswith('Diving'):
                    in_heur_table = False

            # --- eventos de solución en árbol B&B ---
            m = RE_BB_SOL.match(line_stripped)
            if m:
                t    = float(m.group(1))
                node = int(m.group(2))
                src  = m.group(3).strip()
                dual = float(m.group(4))
                prim = float(m.group(5))
                gap  = float(m.group(6))
                stype = _heuristic_type(src)
                result.solution_events.append(SolutionEvent(
                    time_s=t, node=node,
                    primal=prim, dual=dual, gap_pct=gap,
                    source=src, source_type=stype,
                ))
                # comprobar si se alcanza el gap objetivo
                if gap_target is not None and result.time_to_gap_target_s is None:
                    if gap <= gap_target:
                        result.time_to_gap_target_s = t
                continue

            # --- líneas de resumen ---
            m = RE_STATUS.search(line_stripped)
            if m:
                raw = m.group(1).lower()
                if 'optimal' in raw:
                    result.status = 'optimal'
                elif 'infeasible' in raw:
                    result.status = 'infeasible'
                elif 'gap limit' in raw or 'gap_limit' in raw:
                    result.status = 'gap_limit'
                elif 'time limit' in raw or 'time_limit' in raw:
                    result.status = 'time_limit'
                elif 'node limit' in raw:
                    result.status = 'node_limit'
                elif 'solution limit' in raw:
                    result.status = 'sol_limit'
                elif 'memory limit' in raw or 'memory' in raw:
                    result.status = 'memory_limit'
                continue

            m = RE_SOLVE_T.search(line_stripped)
            if m:
                result.solving_time_s = float(m.group(1))
                continue

            m = RE_TOTAL_T.search(line_stripped)
            if m:
                result.total_time_s = float(m.group(1))
                continue

            m = RE_NODES.search(line_stripped)
            if m:
                result.nodes = int(m.group(1))
                result.nodes_total = int(m.group(2)) if m.group(2) else result.nodes
                continue

            m = RE_NODES_TOT.search(line_stripped)
            if m:
                result.nodes_total = int(m.group(1))
                continue

            m = RE_PRIMAL.match(line_stripped)
            if m:
                result.primal_bound = float(m.group(1))
                result.n_solutions = int(m.group(2))
                continue

            m = RE_DUAL.match(line_stripped)
            if m:
                result.dual_bound = float(m.group(1))
                continue

            m = RE_GAP.match(line_stripped)
            if m:
                result.gap_final_pct = float(m.group(1))
                continue

            # --- sección Solution detallada ---
            m = RE_FIRST_SOL.search(line_stripped)
            if m:
                result.first_sol_value  = float(m.group(1))
                result.first_sol_node   = int(m.group(2))
                result.first_sol_time_s = float(m.group(3))
                result.first_sol_heuristic = m.group(4)
                continue

            m = RE_GAP_FIRST.search(line_stripped)
            if m:
                val = m.group(1)
                result.first_sol_gap_pct = float('inf') if val == 'infinite' else float(val)
                continue

            m = RE_GAP_LAST.search(line_stripped)
            if m:
                val = m.group(1)
                result.gap_last_sol_pct = float('inf') if val == 'infinite' else float(val)
                continue

            m = RE_BEST_SOL.search(line_stripped)
            if m:
                result.best_sol_value     = float(m.group(1))
                result.best_sol_time_s    = float(m.group(2))
                result.best_sol_heuristic = m.group(3)
                continue

    return result


# ---------------------------------------------------------------------------
# Agregación y resúmenes
# ---------------------------------------------------------------------------

def summarize_by_mode(results: list[SCIPResult]) -> dict:
    """Genera estadísticas agregadas por modo."""
    from statistics import mean, median, stdev

    by_mode = {}
    for r in results:
        by_mode.setdefault(r.mode, []).append(r)

    summary = {}
    for mode, rs in by_mode.items():
        times = [r.solving_time_s for r in rs]
        gaps  = [r.gap_final_pct for r in rs]
        nodes = [r.nodes_total for r in rs]
        fsol  = [r.first_sol_time_s for r in rs if r.first_sol_time_s]
        fgap  = [r.first_sol_gap_pct for r in rs if r.first_sol_gap_pct]
        n_opt = sum(1 for r in rs if r.status == 'optimal')

        summary[mode] = {
            'n_instances': len(rs),
            'n_optimal': n_opt,
            'solving_time': {
                'mean': mean(times), 'median': median(times),
                'min': min(times), 'max': max(times),
                **(({'stdev': stdev(times)} if len(times) > 1 else {}))
            },
            'gap_final_pct': {
                'mean': mean(gaps), 'median': median(gaps),
                'min': min(gaps), 'max': max(gaps),
            },
            'nodes_total': {
                'mean': mean(nodes), 'median': median(nodes),
                'min': min(nodes), 'max': max(nodes),
            },
            'first_sol_time_s': {
                'mean': mean(fsol) if fsol else None,
                'median': median(fsol) if fsol else None,
            },
            'first_sol_gap_pct': {
                'mean': mean(fgap) if fgap else None,
                'median': median(fgap) if fgap else None,
            },
        }

        # heurísticas que encontraron la primera/mejor solución
        first_heur_counts = {}
        best_heur_counts  = {}
        for r in rs:
            if r.first_sol_heuristic:
                first_heur_counts[r.first_sol_heuristic] = first_heur_counts.get(r.first_sol_heuristic, 0) + 1
            if r.best_sol_heuristic:
                best_heur_counts[r.best_sol_heuristic] = best_heur_counts.get(r.best_sol_heuristic, 0) + 1
        summary[mode]['first_solution_by_heuristic'] = first_heur_counts
        summary[mode]['best_solution_by_heuristic']  = best_heur_counts

        # top heurísticas por tiempo total acumulado (entre instancias)
        heur_time_total = {}
        heur_found_total = {}
        heur_best_total = {}
        for r in rs:
            for h in r.heuristic_stats:
                heur_time_total[h.name]  = heur_time_total.get(h.name, 0) + h.exec_time_s
                heur_found_total[h.name] = heur_found_total.get(h.name, 0) + h.found
                heur_best_total[h.name]  = heur_best_total.get(h.name, 0) + h.best
        summary[mode]['heuristic_totals'] = {
            name: {
                'total_exec_time_s': heur_time_total[name],
                'total_found': heur_found_total[name],
                'total_best': heur_best_total[name],
            }
            for name in sorted(heur_time_total, key=lambda x: -heur_time_total[x])
            if heur_time_total[name] > 0 or heur_found_total[name] > 0
        }

    return summary


# ---------------------------------------------------------------------------
# Exportación CSV
# ---------------------------------------------------------------------------

FLAT_FIELDS = [
    'filename', 'problem', 'instance', 'mode', 'gap_target',
    'status', 'solving_time_s', 'total_time_s',
    'nodes', 'nodes_total', 'n_solutions',
    'primal_bound', 'dual_bound', 'gap_final_pct',
    'first_sol_value', 'first_sol_time_s', 'first_sol_node',
    'first_sol_gap_pct', 'first_sol_heuristic',
    'best_sol_value', 'best_sol_time_s', 'best_sol_heuristic',
    'gap_last_sol_pct', 'time_to_gap_target_s',
]

def results_to_csv(results: list[SCIPResult], path: str):
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FLAT_FIELDS)
        writer.writeheader()
        for r in results:
            row = {k: getattr(r, k) for k in FLAT_FIELDS if k != 'instance'}
            # 'problem' ya es la instancia limpia; 'instance' es un alias explícito
            row['instance'] = r.problem
            writer.writerow(row)


def heuristics_to_csv(results: list[SCIPResult], path: str):
    """CSV detallado de la tabla de heurísticas por instancia."""
    fields = ['instance', 'mode', 'gap_target',
              'heuristic', 'exec_time_s', 'setup_time_s',
              'calls', 'found', 'best']
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in results:
            for h in r.heuristic_stats:
                writer.writerow({
                    'instance': r.problem, 'mode': r.mode,
                    'gap_target': r.gap_target,
                    'heuristic': h.name,
                    'exec_time_s': h.exec_time_s,
                    'setup_time_s': h.setup_time_s,
                    'calls': h.calls, 'found': h.found, 'best': h.best,
                })


def sol_events_to_csv(results: list[SCIPResult], path: str):
    """CSV de la secuencia de mejoras de solución por instancia."""
    fields = ['instance', 'mode', 'gap_target',
              'event_idx', 'time_s', 'node',
              'primal', 'dual', 'gap_pct', 'source', 'source_type']
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in results:
            for i, ev in enumerate(r.solution_events):
                writer.writerow({
                    'instance': r.problem, 'mode': r.mode,
                    'gap_target': r.gap_target,
                    'event_idx': i,
                    'time_s': ev.time_s, 'node': ev.node,
                    'primal': ev.primal, 'dual': ev.dual,
                    'gap_pct': ev.gap_pct, 'source': ev.source,
                    'source_type': ev.source_type,
                })


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Parser de logs SCIP para benchmark de heurísticas')
    parser.add_argument('inputs', nargs='+', help='Archivos .log o directorio')
    parser.add_argument('--output', '-o', default='resultados',
                        help='Prefijo de los CSV de salida (default: resultados)')
    parser.add_argument('--json', action='store_true',
                        help='Exportar también resumen en JSON')
    args = parser.parse_args()

    # recoger ficheros
    log_files = []
    for inp in args.inputs:
        p = Path(inp)
        if p.is_dir():
            log_files.extend(p.glob('*_resultado.log'))
        elif p.is_file():
            log_files.append(p)
        else:
            print(f"  [WARN] no encontrado: {inp}", file=sys.stderr)

    if not log_files:
        print("No se encontraron logs.", file=sys.stderr)
        sys.exit(1)

    print(f"Procesando {len(log_files)} log(s)...")
    results = []
    for lf in sorted(log_files):
        r = parse_log(str(lf))
        results.append(r)
        print(f"  {r.filename:50s}  status={r.status:10s}  t={r.solving_time_s:.1f}s  "
              f"gap={r.gap_final_pct:.2f}%  1ª_sol={r.first_sol_heuristic}")

    # CSV principal
    csv_main = f"{args.output}_summary.csv"
    results_to_csv(results, csv_main)
    print(f"\n→ {csv_main}")

    # CSV heurísticas detallado
    csv_heur = f"{args.output}_heuristics.csv"
    heuristics_to_csv(results, csv_heur)
    print(f"→ {csv_heur}")

    # CSV eventos de solución
    csv_ev = f"{args.output}_solution_events.csv"
    sol_events_to_csv(results, csv_ev)
    print(f"→ {csv_ev}")

    # Resumen por modo
    summary = summarize_by_mode(results)
    print("\n" + "="*60)
    print("RESUMEN POR MODO")
    print("="*60)
    for mode, s in summary.items():
        print(f"\n[{mode}]  {s['n_instances']} instancias  "
              f"({s['n_optimal']} óptimas)")
        st = s['solving_time']
        print(f"  Tiempo resolución (s): media={st['mean']:.1f}  "
              f"mediana={st['median']:.1f}  "
              f"[{st['min']:.1f} - {st['max']:.1f}]")
        gf = s['gap_final_pct']
        def _fmt_gap(v):
            return "inf" if v == float('inf') else f"{v:.2f}"
        print(f"  Gap final (%):         media={_fmt_gap(gf['mean'])}  "
              f"mediana={_fmt_gap(gf['median'])}")
        nd = s['nodes_total']
        print(f"  Nodos totales:         media={nd['mean']:.0f}  "
              f"mediana={nd['median']:.0f}")
        if s['first_sol_time_s']['mean'] is not None:
            ft = s['first_sol_time_s']
            fg = s['first_sol_gap_pct']
            gap_str = f"{fg['mean']:.2f}%" if fg['mean'] is not None else "n/a"
            print(f"  1ª solución (s):       media={ft['mean']:.1f}  gap={gap_str}")
        if s['first_solution_by_heuristic']:
            print(f"  1ª solución por heur:  {s['first_solution_by_heuristic']}")
        if s['best_solution_by_heuristic']:
            print(f"  Mejor sol por heur:    {s['best_solution_by_heuristic']}")
        top_heurs = [(k, v) for k, v in s['heuristic_totals'].items() if v['total_found'] > 0]
        if top_heurs:
            print(f"  Heurísticas que encontraron soluciones:")
            for name, h in sorted(top_heurs, key=lambda x: -x[1]['total_best']):
                print(f"    {name:25s}  found={h['total_found']}  best={h['total_best']}  "
                      f"t={h['total_exec_time_s']:.1f}s")

    if args.json:
        json_path = f"{args.output}_summary.json"
        with open(json_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"\n→ {json_path}")


if __name__ == '__main__':
    main()