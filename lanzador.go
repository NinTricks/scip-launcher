package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"
)

const (
	DirectorioInstancias   = "./miplib"
	LimiteTiempo           = "7200"
	MaxProcesosSimultaneos = 20
)

var ModosValidos = []string{"default", "agresivo", "sin_heuristicas"}

// ─────────────────────────────────────────────
// Tipos
// ─────────────────────────────────────────────

type HeuristicaStat struct {
	Nombre   string
	ExecTime float64
	Calls    int
	Found    int
	Best     int
}

type ResultadoProblema struct {
	Archivo     string
	Modo        string
	Estado      string
	TiempoTotal float64
	Nodos       int
	PrimalBound float64
	DualBound   float64
	Gap         string
	Soluciones  int
	PrimeraSol  string
	MejorSol    string
	Heuristicas []HeuristicaStat
}

// ─────────────────────────────────────────────
// main
// ─────────────────────────────────────────────

func main() {
	archivos, err := recopilarArchivos(DirectorioInstancias)
	if err != nil || len(archivos) == 0 {
		fmt.Printf("No se encontraron instancias en %s: %v\n", DirectorioInstancias, err)
		os.Exit(1)
	}

	// Filtra modos si el usuario los pasa como argumento, si no ejecuta todos.
	modos := ModosValidos
	if len(os.Args) > 1 {
		for _, arg := range os.Args[1:] {
			if !modoValido(arg) {
				fmt.Printf("Modo '%s' no reconocido. Disponibles: %s\n", arg, strings.Join(ModosValidos, " | "))
				os.Exit(1)
			}
		}
		modos = os.Args[1:]
	}

	fmt.Printf("Instancias: %d | Modos: %s | Workers: %d\n",
		len(archivos), strings.Join(modos, ", "), MaxProcesosSimultaneos)

	// Ejecuta cada modo en secuencia (los problemas dentro de cada modo van en paralelo).
	for _, modo := range modos {
		fmt.Printf("\n▶ Iniciando modo: %s\n", strings.ToUpper(modo))
		ejecutarBateria(archivos, modo)
	}

	fmt.Println("\n--- Batería de pruebas finalizada ---")
}

// ─────────────────────────────────────────────
// Recopilación de archivos
// ─────────────────────────────────────────────

// recopilarArchivos busca archivos .lp y .mps en el directorio dado.
func recopilarArchivos(dir string) ([]string, error) {
	var archivos []string
	for _, patron := range []string{"*.lp", "*.mps", "*.LP", "*.MPS"} {
		matches, err := filepath.Glob(filepath.Join(dir, patron))
		if err != nil {
			return nil, err
		}
		archivos = append(archivos, matches...)
	}
	// Elimina duplicados (por si el sistema de ficheros no distingue mayúsculas).
	archivos = deduplicar(archivos)
	sort.Strings(archivos)
	return archivos, nil
}

func deduplicar(s []string) []string {
	seen := make(map[string]struct{}, len(s))
	out := s[:0]
	for _, v := range s {
		if _, ok := seen[v]; !ok {
			seen[v] = struct{}{}
			out = append(out, v)
		}
	}
	return out
}

// ─────────────────────────────────────────────
// Ejecución paralela de una batería
// ─────────────────────────────────────────────

func ejecutarBateria(archivos []string, modo string) []ResultadoProblema {
	numCPU := runtime.NumCPU()
	workers := MaxProcesosSimultaneos
	if workers > numCPU/2 {
		workers = numCPU / 2
	}

	tareas := make(chan string, len(archivos))
	resultadosCh := make(chan ResultadoProblema, len(archivos))

	var wg sync.WaitGroup
	for id := 0; id < workers; id++ {
		wg.Add(1)
		cpuID := id % (numCPU / 2) // garantiza que el ID de CPU es siempre válido
		// tira por las CPUS pares (intención de mejorar
		// fallos en cache
		go func(workerID, cpu int) {
			defer wg.Done()
			for archivo := range tareas {
				res := ejecutarTarea(workerID, cpu*2, archivo, modo)
				resultadosCh <- res
			}
		}(id, cpuID)
	}

	for _, a := range archivos {
		tareas <- a
	}
	close(tareas)

	// Espera a que todos los workers terminen antes de cerrar el canal.
	wg.Wait()
	close(resultadosCh)

	// Recoge resultados en un slice (evita depender del buffer del canal).
	var resultados []ResultadoProblema
	for r := range resultadosCh {
		resultados = append(resultados, r)
	}
	return resultados
}

// ─────────────────────────────────────────────
// Tarea individual
// ─────────────────────────────────────────────

func ejecutarTarea(workerID, cpuID int, rutaArchivo, modo string) ResultadoProblema {
	nombreArchivo := filepath.Base(rutaArchivo)
	resultado := ResultadoProblema{Archivo: nombreArchivo, Modo: modo}

	cmd := exec.Command(
		"taskset", "-c", strconv.Itoa(cpuID),
		"hugectl", "--heap",
		"python", "scip.py", rutaArchivo, LimiteTiempo, modo,
	)

	salida, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("[W%02d/cpu%d] ✗ %s (%s): %v\n", workerID, cpuID, nombreArchivo, modo, err)
		resultado.Estado = "error"
		return resultado
	}

	resultado = parsearSalida(nombreArchivo, modo, string(salida))
	fmt.Printf("[W%02d/cpu%d] ✓ %-30s | %s | estado=%-12s gap=%-10s primera_sol=%s\n",
		workerID, cpuID, nombreArchivo, modo, resultado.Estado, resultado.Gap, resultado.PrimeraSol)
	return resultado
}

// ─────────────────────────────────────────────
// Parsing de salida SCIP
// ─────────────────────────────────────────────

var (
	reEstado     = regexp.MustCompile(`Estado de la solución:\s*(\S+)`)
	reTiempo     = regexp.MustCompile(`Solving Time \(sec\)\s*:\s*([\d.]+)`)
	reNodos      = regexp.MustCompile(`Solving Nodes\s*:\s*(\d+)`)
	rePrimal     = regexp.MustCompile(`Primal Bound\s*:\s*([-\d.e+]+)`)
	reDual       = regexp.MustCompile(`Dual Bound\s*:\s*([-\d.e+]+)`)
	reGap        = regexp.MustCompile(`Gap\s*:\s*([\d.]+\s*%)`)
	reSols       = regexp.MustCompile(`Solutions found\s*:\s*(\d+)`)
	rePrimeraSol = regexp.MustCompile(`First Solution.*?found by <([^>]+)>`)
	reMejorSol   = regexp.MustCompile(`Primal Bound\s*:[-\d.e+\s]+\(.*?found by <([^>]+)>`)
	// Fila de tabla de heurísticas: nombre (puede tener espacios) seguido de 5 números.
	reHeur = regexp.MustCompile(`^\s{2}([\w][\w\s]*[\w]|[\w])\s+:\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+(\d+)\s+(\d+)`)
)

func parsearSalida(archivo, modo, texto string) ResultadoProblema {
	r := ResultadoProblema{Archivo: archivo, Modo: modo}

	if m := reEstado.FindStringSubmatch(texto); m != nil {
		r.Estado = m[1]
	} else {
		switch {
		case strings.Contains(texto, "optimal solution found"):
			r.Estado = "optimal"
		case strings.Contains(texto, "time limit reached"):
			r.Estado = "timelimit"
		case strings.Contains(texto, "infeasible"):
			r.Estado = "infeasible"
		case strings.Contains(texto, "unbounded"):
			r.Estado = "unbounded"
		default:
			r.Estado = "unknown"
		}
	}

	if m := reTiempo.FindStringSubmatch(texto); m != nil {
		r.TiempoTotal, _ = strconv.ParseFloat(m[1], 64)
	}
	if m := reNodos.FindStringSubmatch(texto); m != nil {
		r.Nodos, _ = strconv.Atoi(m[1])
	}
	if m := rePrimal.FindStringSubmatch(texto); m != nil {
		r.PrimalBound, _ = strconv.ParseFloat(m[1], 64)
	}
	if m := reDual.FindStringSubmatch(texto); m != nil {
		r.DualBound, _ = strconv.ParseFloat(m[1], 64)
	}
	if m := reGap.FindStringSubmatch(texto); m != nil {
		r.Gap = strings.TrimSpace(m[1])
	}
	if m := reSols.FindStringSubmatch(texto); m != nil {
		r.Soluciones, _ = strconv.Atoi(m[1])
	}
	if m := rePrimeraSol.FindStringSubmatch(texto); m != nil {
		r.PrimeraSol = m[1]
	}
	if m := reMejorSol.FindStringSubmatch(texto); m != nil {
		r.MejorSol = m[1]
	}

	r.Heuristicas = parsearHeuristicas(texto)
	return r
}

// parsearHeuristicas extrae la tabla "Primal Heuristics" de la salida de SCIP.
// Usa el patrón de cabecera para entrar en la sección y detección robusta de fin:
// cualquier línea no vacía que no encaje con el regex de fila termina la sección.
func parsearHeuristicas(texto string) []HeuristicaStat {
	var heurísticas []HeuristicaStat
	enSeccion := false

	for _, linea := range strings.Split(texto, "\n") {
		if !enSeccion {
			if strings.Contains(linea, "Primal Heuristics") && strings.Contains(linea, "ExecTime") {
				enSeccion = true
			}
			continue
		}

		trimmed := strings.TrimSpace(linea)
		if trimmed == "" {
			continue // ignora líneas en blanco dentro de la sección
		}

		m := reHeur.FindStringSubmatch(linea)
		if m == nil {
			// Primera línea no vacía que no encaja → fin de la sección
			break
		}

		calls, _ := strconv.Atoi(m[4])
		found, _ := strconv.Atoi(m[5])
		best, _ := strconv.Atoi(m[6])
		execTime, _ := strconv.ParseFloat(m[2], 64)

		heurísticas = append(heurísticas, HeuristicaStat{
			Nombre:   strings.TrimSpace(m[1]),
			ExecTime: execTime,
			Calls:    calls,
			Found:    found,
			Best:     best,
		})
	}
	return heurísticas
}

// ─────────────────────────────────────────────
// Utilidades
// ─────────────────────────────────────────────

func modoValido(modo string) bool {
	for _, m := range ModosValidos {
		if m == modo {
			return true
		}
	}
	return false
}

func porcentaje(parte, total int) float64 {
	if total == 0 {
		return 0
	}
	return float64(parte) / float64(total) * 100
}

func sortedKeys(m map[string]*HeuristicaStat) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

func mejorHeuristica(m map[string]*HeuristicaStat) string {
	var mejor *HeuristicaStat
	for _, h := range m {
		if mejor == nil || h.Best > mejor.Best {
			mejor = h
		}
	}
	if mejor == nil || mejor.Best == 0 {
		return "ninguna"
	}
	return fmt.Sprintf("%s (best=%d)", mejor.Nombre, mejor.Best)
}
