"""
Prioridad de Procesos - Comparacion simultanea
Taller de Sistemas Operativos - Ejercicio 4 (segunda prueba)

Launches two processes that run exactly the same calculation at the same
time, one with low priority and one with high priority, and compares them.
Usage:
    python comparar_prioridades.py              (both on the same core)
    python comparar_prioridades.py --sin-afinidad  (Windows picks the cores)
"""

import multiprocessing
import sys

import psutil

from prioridad import WORK_LIMIT, print_record, run_task, save_results

PRIORITY_A = "low"
PRIORITY_B = "high"
ROUNDS = 3          # repeat the test to reduce the effect of random noise


def worker(priority_name, label, affinity, barrier, queue):
    queue.put(run_task(priority_name, label, affinity, barrier))


def run_round(round_number, affinity):
    barrier = multiprocessing.Barrier(2)
    queue = multiprocessing.Queue()

    # Alternate the launch order each round so neither process has an advantage
    tasks = [(PRIORITY_A, "A"), (PRIORITY_B, "B")]
    if round_number % 2 == 0:
        tasks.reverse()

    processes = [
        multiprocessing.Process(target=worker,
                                args=(priority, f"{label}-{priority}", affinity, barrier, queue))
        for priority, label in tasks
    ]
    for process in processes:
        process.start()

    records = [queue.get() for _ in processes]
    for process in processes:
        process.join()

    # Turnaround time: from the common start until each process finishes.
    # A starved process may not even record its own start until much later,
    # so its "wall_seconds" alone would hide the time it spent waiting.
    common_start = min(record["start_epoch"] for record in records)
    for record in records:
        record["turnaround_seconds"] = round(record["end_epoch"] - common_start, 3)

    # Sort by end time to show who finished first
    return sorted(records, key=lambda record: record["end_epoch"])


def main():
    if "realtime" in (PRIORITY_A, PRIORITY_B):
        print("REALTIME no se permite en la comparacion simultanea. Use prioridad.py.")
        return

    use_affinity = "--sin-afinidad" not in sys.argv
    # Pin both processes to the same core so they really compete for it.
    # With many free cores each process would get its own core and the
    # priority would have almost nothing to decide.
    affinity = [psutil.Process().cpu_affinity()[0]] if use_affinity else None

    print("=" * 60)
    print("   COMPARACION DE PRIORIDADES (dos procesos simultaneos)")
    print("=" * 60)
    print(f"Proceso A: {PRIORITY_A.upper()}   |   Proceso B: {PRIORITY_B.upper()}")
    print(f"Calculo: contar primos menores que {WORK_LIMIT:,}")
    print(f"Nucleos logicos del equipo: {psutil.cpu_count()}")
    print("Afinidad: " + (f"ambos en el nucleo {affinity[0]}" if affinity else "libre (Windows decide)"))
    print(f"Rondas: {ROUNDS}\n")

    totals = {PRIORITY_A: [], PRIORITY_B: []}

    try:
        for round_number in range(1, ROUNDS + 1):
            print(f"--- Ronda {round_number} de {ROUNDS} ---")
            records = run_round(round_number, affinity)
            for record in records:
                print_record(record)
                print()
                totals[record["requested_priority"].lower()].append(record["turnaround_seconds"])
            print(f"Termino primero: {records[0]['label']} (PID {records[0]['pid']})\n")
            save_results(records)
    except KeyboardInterrupt:
        print("\nComparacion interrumpida por el usuario.")
        return

    print("=" * 60)
    print("RESUMEN (tiempo de retorno promedio)")
    print("=" * 60)
    for priority, durations in totals.items():
        average = sum(durations) / len(durations)
        print(f"  {priority.upper():<14} {average:7.3f} s   ({', '.join(str(d) for d in durations)})")
    print("\nResultados guardados en resultados_prioridad.csv")


if __name__ == "__main__":
    main()
