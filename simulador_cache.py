"""
Simulador de Memoria Cache (L1/L2 vs RAM)
Taller de Sistemas Operativos - Ejercicio 2

Didactic simulation: a Python dictionary plays the role of a fast memory
that keeps data already read, so the program avoids going back to disk.
"""

import os
import time
from pathlib import Path

# Configuration constants
FILE_PATH = Path(__file__).parent / "archivo_grande.txt"
TARGET_SIZE_MB = 50            # size of the generated test file
NUM_READS = 5                  # requests of the same file in the demo
BENCHMARK_REPETITIONS = 10     # repetitions used to compute averages


class FileCache:
    """Cache that stores file contents in RAM using a dictionary."""

    def __init__(self):
        self.storage = {}      # key: absolute file path, value: file content
        self.disk_reads = 0
        self.hits = 0
        self.misses = 0

    def read_file(self, path):
        # abspath only works with the text of the path, it does not touch the disk
        key = os.path.abspath(path)

        # CACHE HIT: the content is already in RAM, open() is not used
        if key in self.storage:
            self.hits += 1
            return self.storage[key], "HIT"

        # CACHE MISS: read from disk and save a copy in the cache
        self.misses += 1
        content = read_from_disk(path)
        self.disk_reads += 1
        self.storage[key] = content
        return content, "MISS"


def read_from_disk(path):
    # This is the only place in the program where the file is opened
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def create_test_file(path, size_mb):
    print(f"El archivo {path.name} no existe. Generando uno de {size_mb} MB...")
    line = "Linea de prueba para el simulador de memoria cache - Sistemas Operativos\n"
    target_bytes = size_mb * 1024 * 1024
    total_lines = target_bytes // (len(line) + 9)   # 9 = line number + space

    # newline="\n" keeps one byte per line break, so bytes == characters
    with open(path, "w", encoding="utf-8", newline="\n") as file:
        for number in range(total_lines):
            file.write(f"{number:08d} {line}")
    print("Archivo generado correctamente.\n")


def format_ms(seconds):
    return f"{seconds * 1000:.4f} ms"


def run_demo(cache, path):
    print("-" * 60)
    print(f"DEMOSTRACION: {NUM_READS} solicitudes del mismo archivo")
    print("-" * 60)

    disk_time = None
    cache_times = []

    for request in range(1, NUM_READS + 1):
        start = time.perf_counter()
        content, result = cache.read_file(path)
        elapsed = time.perf_counter() - start

        if result == "MISS":
            disk_time = elapsed
            print(f"Lectura {request}: CACHE MISS -> DISCO -> CACHE  "
                  f"({format_ms(elapsed)}, {len(content):,} caracteres)")
        else:
            cache_times.append(elapsed)
            print(f"Lectura {request}: CACHE HIT  -> CACHE           "
                  f"({format_ms(elapsed)}, {len(content):,} caracteres)")

    return disk_time, cache_times, len(content)


def run_benchmark(cache, path, repetitions):
    # Disk reads call read_from_disk directly to skip the cache on purpose
    disk_total = 0.0
    for _ in range(repetitions):
        start = time.perf_counter()
        read_from_disk(path)
        disk_total += time.perf_counter() - start

    cache_total = 0.0
    for _ in range(repetitions):
        start = time.perf_counter()
        cache.read_file(path)
        cache_total += time.perf_counter() - start

    return disk_total / repetitions, cache_total / repetitions


def print_comparison(label_disk, disk_time, label_cache, cache_time):
    print(f"{label_disk:<32}{format_ms(disk_time)}")
    print(f"{label_cache:<32}{format_ms(cache_time)}")
    # Guard against division by zero if the timer resolution is too low
    if cache_time > 0:
        print(f"{'La cache fue aprox.':<32}{disk_time / cache_time:,.0f} veces mas rapida")


def main():
    print("=" * 60)
    print("     SIMULADOR DE MEMORIA CACHE (L1/L2 vs RAM)")
    print("=" * 60)

    try:
        if not FILE_PATH.exists():
            create_test_file(FILE_PATH, TARGET_SIZE_MB)

        file_size = os.path.getsize(FILE_PATH)
        print(f"Archivo: {FILE_PATH.name}")
        print(f"Tamano en disco: {file_size:,} bytes ({file_size / (1024 * 1024):.2f} MB)\n")

        cache = FileCache()
        disk_time, cache_times, char_count = run_demo(cache, FILE_PATH)
        avg_cache_time = sum(cache_times) / len(cache_times)

        print("\n" + "-" * 60)
        print("RESUMEN")
        print("-" * 60)
        print(f"{'Tamano del archivo:':<32}{file_size:,} bytes")
        print(f"{'Caracteres recuperados:':<32}{char_count:,}")
        print_comparison("Tiempo desde disco:", disk_time,
                         "Tiempo promedio desde cache:", avg_cache_time)
        print(f"{'Accesos al disco:':<32}{cache.disk_reads}")
        print(f"{'CACHE HITS:':<32}{cache.hits}")
        print(f"{'CACHE MISSES:':<32}{cache.misses}")

        print("\n" + "-" * 60)
        print(f"PROMEDIOS ({BENCHMARK_REPETITIONS} repeticiones de cada tipo)")
        print("-" * 60)
        avg_disk, avg_cache = run_benchmark(cache, FILE_PATH, BENCHMARK_REPETITIONS)
        print_comparison("Promedio leyendo del disco:", avg_disk,
                         "Promedio leyendo de cache:", avg_cache)

    except OSError as error:
        print(f"\nError de archivo: {error}")
    except MemoryError:
        print("\nNo hay suficiente memoria RAM para guardar el archivo en cache.")


if __name__ == "__main__":
    main()
