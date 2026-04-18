from pyscipopt import *
import sys
import os



if len(sys.argv) < 3:
    print("Error en los parametros: archivo tiempo")
    sys.exit(1)

NOMBRE_PROBLEMA = sys.argv[1]
LIMITE_TIEMPO = float(sys.argv[2])
NOMBRE_LOG = NOMBRE_PROBLEMA.split('.')[0] + "_resultado.log"

if os.path.exists(NOMBRE_LOG):
    os.remove(NOMBRE_LOG)

###################################################################### MAIN
model = Model()
model.readProblem(NOMBRE_PROBLEMA)


model.setLogfile(NOMBRE_LOG)

model.setParam("limits/time", LIMITE_TIEMPO)

#model.setPresolve(SCIP_PARAMSETTING.OFF)
#model.setSeparating(SCIP_PARAMSETTING.OFF)
#model.setHeuristics(SCIP_PARAMSETTING.OFF)

model.setParam("display/freq", 5000)
model.setParam("display/lpinfo", False)

model.optimize()
model.printStatistics()


with open(NOMBRE_LOG, "a") as f:
    f.write("\n" + "="*50 + "\n")
    f.write("RESUMEN DE RESULTADOS\n")
    f.write("="*50 + "\n")

    status = model.getStatus()
    f.write(f"Estado de la solución: {status}\n")

    # Intentar obtener la mejor solución
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
