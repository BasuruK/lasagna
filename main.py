import os
import threading
import subprocess
from lasagna import RAG

# Ram min config level in MB
mem_config_level_min = 500
mem_config_level_medium = 5000
mem_status = RAG.GREEN

# CPU Utilization config level
cpu_config_level_min = 10
cpu_config_level_medium = 30
cpu_status = RAG.GREEN

# HDD Utilization config level
hdd_config_level_min = 1000
hdd_config_level_medium = 10000
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


def check_cpu_utilization_level():
    cpu_util = subprocess.Popen("mpstat | awk -F ' ' '{print $12}'", stdout=subprocess.PIPE, shell=True)
    cpu_util = int(str(cpu_util.communicate()[0]).split("\\n")[3])

    if cpu_util <= cpu_config_level_min:
        return RAG.RED
    elif cpu_config_level_medium <= cpu_util <= cpu_config_level_min:
        return RAG.AMBER
    elif cpu_util > cpu_config_level_medium:
        return RAG.GREEN


def check_hdd_utilization_level():
    hdd_util = subprocess.Popen("df | grep '/dev/sda2' | awk -F ' ' '{print $4}'", stdout=subprocess.PIPE, shell=True)
    # hdd_util = int(str(hdd_util.communicate()[0]).split("\\n"))
    hdd_util = int(str(hdd_util.communicate()[0]).split("'")[1].split("\\n")[0])

    if hdd_util <= hdd_config_level_min:
        return RAG.RED
    elif hdd_config_level_medium < hdd_util <= hdd_config_level_min:
        return RAG.AMBER
    elif hdd_util > hdd_config_level_medium:
        return RAG.GREEN


def check_file_modification_time():
    return True


def check_mysql_status():
    return True


def check_telnet_status():
    return True

    
# Main functionality
while True:
    print(check_hdd_utilization_level())
    break
