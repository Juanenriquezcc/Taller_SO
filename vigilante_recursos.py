"""
Vigilante de Recursos - Monitoreo de RAM y CPU
Taller de Sistemas Operativos - Ejercicio 1
"""

import time
from datetime import datetime

import psutil

# Configuration constants
RAM_THRESHOLD = 80.0          # percent of RAM that triggers the alert
INTERVAL_SECONDS = 2          # time between each reading
LOG_FILE = "registro_recursos.txt"


def get_cpu_usage():
    # interval=1 makes psutil compare CPU times over 1 second,
    # so the value is accurate and the call also acts as a pause
    return psutil.cpu_percent(interval=1)


def get_ram_usage():
    # virtual_memory() returns a named tuple, .percent is the used RAM in %
    return psutil.virtual_memory().percent


def write_log(ram_percent, cpu_percent):
    now = datetime.now()
    line = (
        f"Fecha: {now.strftime('%Y-%m-%d')} | "
        f"Hora: {now.strftime('%H:%M:%S')} | "
        f"RAM: {ram_percent:.1f}% | "
        f"CPU: {cpu_percent:.1f}%\n"
    )
    # "a" mode appends to the file; "with" closes it automatically
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as file:
            file.write(line)
    except OSError as error:
        print(f"  No se pudo escribir en {LOG_FILE}: {error}")


def show_status(ram_percent, cpu_percent):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] CPU: {cpu_percent:5.1f}%  |  RAM: {ram_percent:5.1f}%")


def show_alert(ram_percent):
    print("!" * 55)
    print(f"  ALERTA: la RAM supero el {RAM_THRESHOLD:.0f}% (uso actual: {ram_percent:.1f}%)")
    print(f"  Evento registrado en {LOG_FILE}")
    print("!" * 55)


def main():
    print("=" * 55)
    print("        VIGILANTE DE RECURSOS - MONITOR INICIADO")
    print("=" * 55)
    print(f"Umbral de alerta de RAM: {RAM_THRESHOLD:.0f}%")
    print("Presione Ctrl+C para detener el monitoreo.\n")

    # State flag: True while RAM stays above the threshold.
    # Only the transition from normal -> high is logged, so the file
    # gets one entry per overload episode instead of one per iteration.
    alert_active = False

    try:
        while True:
            cpu_percent = get_cpu_usage()
            ram_percent = get_ram_usage()
            show_status(ram_percent, cpu_percent)

            if ram_percent > RAM_THRESHOLD:
                if not alert_active:
                    show_alert(ram_percent)
                    write_log(ram_percent, cpu_percent)
                    alert_active = True
            elif alert_active:
                print("  La RAM volvio a niveles normales.")
                alert_active = False

            # Sleep so the loop does not waste CPU (busy waiting)
            time.sleep(INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\n\nMonitoreo detenido por el usuario. Hasta luego.")
    except psutil.Error as error:
        print(f"\nError al leer los recursos del sistema: {error}")
    except Exception as error:
        print(f"\nError inesperado: {error}")


if __name__ == "__main__":
    main()
