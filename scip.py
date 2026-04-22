from pyscipopt import *
import sys
import os

class PrimeraSolucionHandler(Eventhdlr):
    
    def eventinit(self):
        # Suscribirse al evento de mejor solución encontrada
        self.model.catchEvent(SCIP_EVENTTYPE.BESTSOLFOUND, self)
    
    def eventexit(self):
        self.model.dropEvent(SCIP_EVENTTYPE.BESTSOLFOUND, self)
    
    def eventexec(self, event):
        # Solo actuar en la primera solución
        if self.model.getNSols() == 1:
            print("Primera solución encontrada! Cambiando a configuración OPTIMALITY...")
            self.model.setHeuristics(SCIP_PARAMSETTING.DEFAULT)
            self.model.setSeparating(SCIP_PARAMSETTING.DEFAULT)
            self.model.setPresolve(SCIP_PARAMSETTING.DEFAULT)

if len(sys.argv) < 3:
    print("Error en los parametros: archivo tiempo [modo] [gap]")
    print("  modos: default | agresivo | sin_heuristicas | inteligente")
    print("  gap: valor en % (ej: 0.5, 1.0, 5.0) - opcional")
    sys.exit(1)

NOMBRE_PROBLEMA = sys.argv[1]
LIMITE_TIEMPO = float(sys.argv[2])
MODO = sys.argv[3] if len(sys.argv) > 3 else "default"
GAP_OBJETIVO = None

if len(sys.argv) > 4:
    try:
        GAP_OBJETIVO = float(sys.argv[4]) / 100.0  # convertir porcentaje a decimal
    except ValueError:
        print(f"Gap '{sys.argv[4]}' no válido. Usa un número (ej: 0.5)")
        sys.exit(1)

if MODO not in ("default", "agresivo", "sin_heuristicas", "inteligente"):
    print(f"Modo '{MODO}' no reconocido. Usa: default | agresivo | sin_heuristicas | inteligente")
    sys.exit(1)

if GAP_OBJETIVO is not None:
    gap_str = f"{GAP_OBJETIVO*100:.1f}"
    NOMBRE_LOG = NOMBRE_PROBLEMA.split('.')[0] + f"_{MODO}_{gap_str}_resultado.log"
else:
    NOMBRE_LOG = NOMBRE_PROBLEMA.split('.')[0] + f"_{MODO}_resultado.log"
if os.path.exists(NOMBRE_LOG):
    os.remove(NOMBRE_LOG)

model = Model()
model.setParam("limits/memory", 92160)  # 90 GB 
model.readProblem(NOMBRE_PROBLEMA)
model.setLogfile(NOMBRE_LOG)
if LIMITE_TIEMPO != 0:
    model.setParam("limits/time", LIMITE_TIEMPO)
if GAP_OBJETIVO is not None:
    model.setParam("limits/gap", GAP_OBJETIVO)
model.setParam("display/freq", 5000)
model.setParam("display/lpinfo", False)

if MODO == "agresivo":
    model.setHeuristics(SCIP_PARAMSETTING.AGGRESSIVE)
elif MODO == "sin_heuristicas":
    model.setHeuristics(SCIP_PARAMSETTING.OFF)
elif MODO == "inteligente":
    model.setHeuristics(SCIP_PARAMSETTING.AGGRESSIVE)
    model.setSeparating(SCIP_PARAMSETTING.FAST)
    model.setPresolve(SCIP_PARAMSETTING.FAST)
    handler = PrimeraSolucionHandler()
    model.includeEventhdlr(handler, "PrimeraSolucion", "Cambia params tras primera solucion")

#model.setEmphasis(SCIP_PARAMEMPHASIS.FEASIBILITY)

model.optimize()
model.printStatistics()

with open(NOMBRE_LOG, "a") as f:
    f.write("\n" + "="*50 + "\n")
    f.write("RESUMEN DE RESULTADOS\n")
    f.write("="*50 + "\n")
    f.write(f"Modo: {MODO}\n")
    status = model.getStatus()
    f.write(f"Estado de la solución: {status}\n")

    sol = model.getBestSol()
    if sol is not None:
        f.write(f"Valor de la función objetivo: {model.getObjVal()}\n")
        gap = model.getGap()
        f.write(f"Gap final: {gap*100:.2f}%\n\n" if gap < 1e+20 else "Gap: no disponible\n\n")
        # Detectar si se alcanzó el gap objetivo
        if GAP_OBJETIVO is not None and gap <= GAP_OBJETIVO:
            f.write("ESTADO: Gap objetivo alcanzado\n")
        f.write("Variables con valor distinto de cero:\n")
        for v in model.getVars():
            val = model.getSolVal(sol, v)
            if abs(val) > 1e-6:
                f.write(f"{v.name}: {val}\n")
    else:
        f.write("No se encontró ninguna solución factible en el tiempo dado.\n")

    f.write("\n" + "="*50 + "\n")
