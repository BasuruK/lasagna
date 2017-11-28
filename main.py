import os
import threading
import subprocess
from lasagna import RAG
from lasagna import log_manager

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
    ram_mb = float(ram_mb.split(" ")[0]) / 1024

    if ram_mb < mem_config_level_min:
        return RAG.RED
    elif mem_config_level_medium <= ram_mb >= mem_config_level_min:
        return RAG.AMBER
    elif ram_mb > mem_config_level_medium:
        return RAG.GREEN


def check_cpu_utilization_level():
    cpu_util = subprocess.Popen("mpstat | awk -F ' ' '{print $12}'", stdout=subprocess.PIPE, shell=True)
    cpu_util = float(str(cpu_util.communicate()[0]).split("\\n")[3])

    if cpu_util <= cpu_config_level_min:
        return RAG.RED
    elif cpu_config_level_medium <= cpu_util <= cpu_config_level_min:
        return RAG.AMBER
    elif cpu_util > cpu_config_level_medium:
        return RAG.GREEN


def check_hdd_utilization_level():
    hdd_util = subprocess.Popen("df | grep '/dev/sda2' | awk -F ' ' '{print $4}'", stdout=subprocess.PIPE, shell=True)
    # hdd_util = int(str(hdd_util.communicate()[0]).split("\\n"))
    hdd_util = float(str(hdd_util.communicate()[0]).split("'")[1].split("\\n")[0])

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


def get_server_name():
    svr_name = subprocess.Popen("uname -r", stdout=subprocess.PIPE, shell=True)
    return str(svr_name.communicate()).split("'")[1].rsplit("\\n")[0]


def read_file():
    try:
        file = open("check_log.txt", "r+")
        return file
    except FileNotFoundError:
        print("Log File not found")
        print("File will be created")
        open("check_log.txt", 'w').close()
        read_file()


def close_file(file):
    try:
        file.close()
    except FileNotFoundError:
        print("Check_log not found")


# Main functionality
while True:
    server_name = get_server_name()
    ram_utilization = check_ram_utilization_level()
    cpu_utilization = check_cpu_utilization_level()
    hdd_utilization = check_hdd_utilization_level()
    mysql_connection = check_mysql_status()
    telnet_connection = check_telnet_status()

    check_file = read_file()
    check_file.write("Server Name: " + server_name + "\n" +
                     "Ram Utilization: " + str(ram_utilization) + "\n" +
                     "CPU Utilization: " + str(cpu_utilization) + "\n" +
                     "HDD Utilization: " + str(hdd_utilization))
    close_file(check_file)
    break
