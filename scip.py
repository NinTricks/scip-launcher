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
    print("Error en los parametros: archivo tiempo [modo]")
    print("  modos: default | agresivo | sin_heuristicas | inteligente")
    sys.exit(1)

NOMBRE_PROBLEMA = sys.argv[1]
LIMITE_TIEMPO = float(sys.argv[2])
MODO = sys.argv[3] if len(sys.argv) > 3 else "default"

if MODO not in ("default", "agresivo", "sin_heuristicas", "inteligente"):
    print(f"Modo '{MODO}' no reconocido. Usa: default | agresivo | sin_heuristicas | inteligente")
    sys.exit(1)

NOMBRE_LOG = NOMBRE_PROBLEMA.split('.')[0] + f"_{MODO}_resultado.log"
if os.path.exists(NOMBRE_LOG):
    os.remove(NOMBRE_LOG)

model = Model()
model.setParam("limits/memory", 92160)  # 90 GB 
model.readProblem(NOMBRE_PROBLEMA)
model.setLogfile(NOMBRE_LOG)
if LIMITE_TIEMPO != 0:
    model.setParam("limits/time", LIMITE_TIEMPO)
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
        f.write("Variables con valor distinto de cero:\n")
        for v in model.getVars():
            val = model.getSolVal(sol, v)
            if abs(val) > 1e-6:
                f.write(f"{v.name}: {val}\n")
    else:
        f.write("No se encontró ninguna solución factible en el tiempo dado.\n")

    f.write("\n" + "="*50 + "\n")
