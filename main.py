import os
import threading
from lasagna import RAG

# Ram min config level in MB
mem_config_level_min = 500
mem_config_level_medium = 5000
mem_status = RAG.GREEN

# CPU Utilization config level
cpu_config_level = None
cpu_status = RAG.GREEN
# HDD Utilization config level
hdd_config_level = None
hdd_status = RAG.GREEN

def check_ram_utilization_level():
    free_mem = os.popen('cat /proc/meminfo | grep "MemFree"')
    free_mem = free_mem.read()
    # Convert KB to MB
    ram_mb = free_mem.split(":")[1].lstrip()
    ram_mb = int(ram_mb.split(" ")[0]) / 1024

    if ram_mb < mem_config_level_min:
        return RAG.RED
    elif mem_config_level_medium < ram_mb > mem_config_level_min:
        return RAG.AMBER
    elif ram_mb > mem_config_level_medium:
        return RAG.GREEN
    return ram_mb


def check_cpu_utilization_level():
    print(None)


# Main functionality
while True:


