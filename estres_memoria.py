"""
Estres de Memoria y Salto a la Virtual (Paginacion)
Taller de Sistemas Operativos - Ejercicio 3

Progressively fills a list with strings to raise memory pressure, so the
behavior of RAM and virtual memory can be observed in the Task Manager.
Several safety limits stop the test long before the system is at risk.
"""

import os
import time

import psutil

# ---------------- Configuration ----------------
TEST_LEVEL = "suave"           # "suave", "media" or "alta"

PROFILES = {
    "suave": {"max_process_mb": 512,  "max_elements": 500_000,   "max_ram_percent": 92},
    "media": {"max_process_mb": 1024, "max_elements": 1_000_000, "max_ram_percent": 94},
    "alta":  {"max_process_mb": 2048, "max_elements": 2_000_000, "max_ram_percent": 95},
}

MIN_AVAILABLE_MB = 500         # always leave at least this much RAM free
MAX_FRACTION_OF_TOTAL_RAM = 0.40   # the process never takes more than 40% of total RAM
STRING_SIZE = 1024             # characters per string (about 1 KB each)
BATCH_SIZE = 10_000            # strings added per step (about 10 MB)
STEP_DELAY = 0.3               # seconds between steps, so changes can be observed
HOLD_SECONDS = 15              # time the memory is kept before releasing it

MB = 1024 * 1024
GB = 1024 * MB


def get_limits(level):
    if level not in PROFILES:
        raise ValueError(f"Nivel de prueba invalido: '{level}'. Use suave, media o alta.")

    limits = dict(PROFILES[level])
    # Rule 8: never try to take most of the machine memory
    total_mb = psutil.virtual_memory().total / MB
    limits["max_process_mb"] = min(limits["max_process_mb"],
                                   int(total_mb * MAX_FRACTION_OF_TOTAL_RAM))
    return limits


def check_safety(process, limits, element_count):
    """Return the reason to stop, or None if it is safe to continue."""
    ram = psutil.virtual_memory()
    # vms is the memory committed by the process (on Windows it equals the
    # private bytes). It counts pages in RAM and pages sent to the page file,
    # so the limit still works even if Windows pages part of the process out.
    committed_mb = process.memory_info().vms / MB

    if element_count >= limits["max_elements"]:
        return f"se alcanzo el limite de elementos ({limits['max_elements']:,})"
    if committed_mb >= limits["max_process_mb"]:
        return f"el proceso alcanzo el limite de {limits['max_process_mb']} MB"
    if ram.percent >= limits["max_ram_percent"]:
        return f"la RAM del sistema llego al {ram.percent}% (limite {limits['max_ram_percent']}%)"
    if ram.available / MB < MIN_AVAILABLE_MB:
        return f"quedan menos de {MIN_AVAILABLE_MB} MB de RAM disponible"
    return None


def print_status(process, element_count, start_time):
    ram = psutil.virtual_memory()
    swap = psutil.swap_memory()        # on Windows this reports the page file
    info = process.memory_info()
    elapsed = time.perf_counter() - start_time

    print(f"[{elapsed:6.1f} s] Elementos: {element_count:>9,} | "
          f"Proceso: {info.rss / MB:6.0f} MB en RAM, {info.vms / MB:6.0f} MB comprometidos")
    print(f"           RAM sistema: {ram.used / GB:5.2f}/{ram.total / GB:.2f} GB ({ram.percent:4.1f}%) | "
          f"Disponible: {ram.available / GB:5.2f} GB | "
          f"Archivo de paginacion: {swap.used / GB:5.2f} GB ({swap.percent:4.1f}%)")


def show_warning(level, limits):
    print("=" * 75)
    print("        ESTRES DE MEMORIA Y SALTO A LA VIRTUAL (PAGINACION)")
    print("=" * 75)
    print("ADVERTENCIA: este programa aumentara a proposito el consumo de memoria.")
    print("  - Guarde su trabajo y cierre programas pesados antes de continuar.")
    print("  - Abra el Administrador de tareas -> Rendimiento -> Memoria.")
    print("  - Puede detenerlo en cualquier momento con Ctrl+C.\n")
    print(f"Nivel de prueba: {level.upper()}")
    print(f"  Limite de elementos:        {limits['max_elements']:,}")
    print(f"  Limite de memoria proceso:  {limits['max_process_mb']} MB")
    print(f"  Limite de RAM del sistema:  {limits['max_ram_percent']}%")
    print(f"  RAM minima disponible:      {MIN_AVAILABLE_MB} MB\n")

    try:
        answer = input("Escriba S y presione Enter para comenzar: ")
    except EOFError:
        return False
    return answer.strip().lower() == "s"


def fill_memory(data, limits, process, start_time):
    # The fixed part is created once; adding a unique prefix creates a NEW
    # string object each time. Appending the same object repeatedly would
    # only store references and memory would barely grow.
    filler = "X" * (STRING_SIZE - 10)

    while True:
        reason = check_safety(process, limits, len(data))
        if reason:
            return reason

        for _ in range(BATCH_SIZE):
            data.append(f"{len(data):010d}" + filler)

        print_status(process, len(data), start_time)
        time.sleep(STEP_DELAY)


def hold_memory(data, process, start_time):
    print(f"\nManteniendo la memoria ocupada {HOLD_SECONDS} s para observar el Administrador de tareas...")
    for second in range(HOLD_SECONDS):
        time.sleep(1)
        if second % 5 == 4:
            print_status(process, len(data), start_time)


def main():
    try:
        limits = get_limits(TEST_LEVEL)
    except ValueError as error:
        print(error)
        return

    if not show_warning(TEST_LEVEL, limits):
        print("Prueba cancelada por el usuario.")
        return

    process = psutil.Process(os.getpid())
    data = []
    start_time = time.perf_counter()

    # Do not even start if the system is already under the safety margins
    reason = check_safety(process, limits, 0)
    if reason:
        print(f"\nNo es seguro iniciar la prueba: {reason}.")
        print("Cierre algunos programas o elija un nivel mas suave.")
        return

    print("\nEstado inicial:")
    print_status(process, 0, start_time)
    print("\nLlenando memoria...\n")

    try:
        reason = fill_memory(data, limits, process, start_time)
        print(f"\n>>> LIMITE DE SEGURIDAD ALCANZADO: {reason}. Deteniendo el llenado.")
        hold_memory(data, process, start_time)
    except KeyboardInterrupt:
        print("\n\n>>> Prueba detenida por el usuario (Ctrl+C).")
    except MemoryError:
        print("\n\n>>> Python no pudo reservar mas memoria (MemoryError). Deteniendo.")
    finally:
        print("\nLiberando memoria...")
        data.clear()
        time.sleep(1)
        print_status(process, 0, start_time)
        print("\nPrueba finalizada. Observe como baja el uso de RAM en el Administrador de tareas.")


if __name__ == "__main__":
    main()
