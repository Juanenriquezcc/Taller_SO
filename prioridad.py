"""
Prioridad de Procesos (Scheduling)
Taller de Sistemas Operativos - Ejercicio 4

Runs a CPU heavy calculation with a chosen Windows priority class.
Usage:
    python prioridad.py low | normal | above_normal | high | realtime
"""

import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil

# Work size: count prime numbers below this value (about 4 s on a normal PC)
WORK_LIMIT = 1_500_000
RESULTS_FILE = Path(__file__).parent / "resultados_prioridad.csv"

# Command line name -> Windows priority class (constants provided by psutil)
PRIORITY_CLASSES = {
    "low": psutil.BELOW_NORMAL_PRIORITY_CLASS,
    "normal": psutil.NORMAL_PRIORITY_CLASS,
    "above_normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS,
    "high": psutil.HIGH_PRIORITY_CLASS,
    "realtime": psutil.REALTIME_PRIORITY_CLASS,
}

# Reverse map used to show the priority the OS really applied
PRIORITY_NAMES = {
    psutil.IDLE_PRIORITY_CLASS: "IDLE",
    psutil.BELOW_NORMAL_PRIORITY_CLASS: "BELOW_NORMAL",
    psutil.NORMAL_PRIORITY_CLASS: "NORMAL",
    psutil.ABOVE_NORMAL_PRIORITY_CLASS: "ABOVE_NORMAL",
    psutil.HIGH_PRIORITY_CLASS: "HIGH",
    psutil.REALTIME_PRIORITY_CLASS: "REALTIME",
}

CSV_FIELDS = ["label", "pid", "requested_priority", "applied_priority", "affinity",
              "start_time", "end_time", "wall_seconds", "cpu_seconds",
              "turnaround_seconds", "result"]


def is_prime(number):
    if number < 2:
        return False
    if number % 2 == 0:
        return number == 2
    divisor = 3
    while divisor * divisor <= number:
        if number % divisor == 0:
            return False
        divisor += 2
    return True


def heavy_calculation(limit):
    # Pure CPU work: no disk, no network, no sleep
    return sum(1 for number in range(limit) if is_prime(number))


def set_priority(process, priority_name):
    """Set the priority of OUR process and return the class Windows really applied."""
    process.nice(PRIORITY_CLASSES[priority_name])
    # Read it back: without admin rights Windows silently turns REALTIME into HIGH
    return PRIORITY_NAMES.get(process.nice(), str(process.nice()))


def run_task(priority_name, label="", affinity=None, barrier=None):
    """Run the calculation in the current process and return a result record."""
    process = psutil.Process(os.getpid())

    if affinity is not None:
        process.cpu_affinity(affinity)
    applied = set_priority(process, priority_name)

    # Optional synchronization so several processes start at the same moment
    if barrier is not None:
        barrier.wait()

    cpu_before = process.cpu_times()
    start_wall = time.perf_counter()
    start_time = datetime.now()

    result = heavy_calculation(WORK_LIMIT)

    end_time = datetime.now()
    wall_seconds = time.perf_counter() - start_wall
    cpu_after = process.cpu_times()
    cpu_seconds = (cpu_after.user + cpu_after.system) - (cpu_before.user + cpu_before.system)

    return {
        "label": label or priority_name,
        "pid": process.pid,
        "requested_priority": priority_name.upper(),
        "applied_priority": applied,
        "affinity": str(process.cpu_affinity()),
        # Epoch values are comparable between processes (used by the launcher)
        "start_epoch": start_time.timestamp(),
        "end_epoch": end_time.timestamp(),
        "start_time": start_time.strftime("%H:%M:%S.%f")[:-3],
        "end_time": end_time.strftime("%H:%M:%S.%f")[:-3],
        "wall_seconds": round(wall_seconds, 3),
        "cpu_seconds": round(cpu_seconds, 3),
        "result": result,
    }


def save_results(records):
    new_file = not RESULTS_FILE.exists()
    with open(RESULTS_FILE, "a", newline="", encoding="utf-8") as file:
        # extrasaction="ignore" skips the internal epoch values
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS, extrasaction="ignore")
        if new_file:
            writer.writeheader()
        writer.writerows(records)


def print_record(record):
    print(f"  Proceso:             {record['label']}")
    print(f"  PID:                 {record['pid']}")
    print(f"  Prioridad pedida:    {record['requested_priority']}")
    print(f"  Prioridad aplicada:  {record['applied_priority']}")
    print(f"  Afinidad (nucleos):  {record['affinity']}")
    print(f"  Hora de inicio:      {record['start_time']}")
    print(f"  Hora de fin:         {record['end_time']}")
    print(f"  Duracion real:       {record['wall_seconds']} s")
    print(f"  Tiempo de CPU usado: {record['cpu_seconds']} s")
    if "turnaround_seconds" in record:
        print(f"  Tiempo de retorno:   {record['turnaround_seconds']} s (desde la salida comun)")
    print(f"  Resultado:           {record['result']:,} numeros primos menores que {WORK_LIMIT:,}")


def confirm_realtime():
    print("!" * 70)
    print("ADVERTENCIA: PRIORIDAD REALTIME (EXPERIMENTAL)")
    print("  - Un proceso REALTIME puede quitarle la CPU a procesos del sistema,")
    print("    incluidos el mouse, el teclado, el audio y el disco.")
    print("  - Un calculo pesado en REALTIME puede hacer que Windows deje de responder.")
    print("  - Sin permisos de administrador Windows la reduce a HIGH automaticamente.")
    print("  - Solo afecta a este proceso y el calculo usa un unico hilo.")
    print("!" * 70)
    try:
        answer = input("Escriba REALTIME para continuar o Enter para cancelar: ")
    except EOFError:
        return False
    return answer.strip() == "REALTIME"


def main():
    if len(sys.argv) != 2 or sys.argv[1].lower() not in PRIORITY_CLASSES:
        print("Uso: python prioridad.py [low | normal | above_normal | high | realtime]")
        return

    priority_name = sys.argv[1].lower()

    if priority_name == "realtime":
        # With a single core a REALTIME busy loop could freeze the whole system
        if (os.cpu_count() or 1) < 2:
            print("REALTIME no se permite en un equipo con un solo nucleo.")
            return
        if not confirm_realtime():
            print("Prueba REALTIME cancelada.")
            return

    print("=" * 60)
    print(f"  PRIORIDAD DE PROCESOS - prueba con prioridad {priority_name.upper()}")
    print("=" * 60)
    print("Calculando... (no cierre la ventana)\n")

    try:
        record = run_task(priority_name)
    except psutil.AccessDenied:
        print("Windows nego el permiso para cambiar la prioridad.")
        return
    except KeyboardInterrupt:
        print("\nCalculo interrumpido por el usuario.")
        return

    print_record(record)
    save_results([record])
    print(f"\nResultado guardado en {RESULTS_FILE.name}")


if __name__ == "__main__":
    main()
