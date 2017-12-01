import os
import threading
import subprocess
from lasagna import RAG
from lasagna import log_manager
import json
import webbrowser
import MySQLdb
import time
from datetime import datetime

# Open Config Files
with open("config_param.json", "r") as f:
    config_file = json.load(f)

# Connect to the Database
db = MySQLdb.connect(config_file["mysql_hostname"],
                     config_file["mysql_uname"],
                     config_file["mysql_pass"],
                     config_file["mysql_dbname"])
cursor = db.cursor()

# Ram min config level in MB
mem_config_level_min = config_file["MinimumRamLevel"]
mem_config_level_medium = config_file["AmberRamLevel"]
mem_status = RAG.GREEN

# CPU Utilization config level
cpu_config_level_min = config_file["MinimumCpuLevel"]
cpu_config_level_medium = config_file["AmberCpuLevel"]
cpu_status = RAG.GREEN

# HDD Utilization config level
hdd_config_level_min = config_file["MinimumHddLevel"]
hdd_config_level_medium = config_file["AmberHddLevel"]
hdd_status = RAG.GREEN


def check_ram_utilization_level():
    free_mem = os.popen('cat /proc/meminfo | grep "MemFree"')
    free_mem = free_mem.read()
    # Convert KB to MB
    ram_mb = free_mem.split(":")[1].lstrip()
    ram_mb = float(ram_mb.split(" ")[0]) / 1024

    if ram_mb < mem_config_level_min:
        return RAG.RED
    elif mem_config_level_medium > ram_mb > mem_config_level_min:
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
    file_mod_time = str(subprocess.Popen("find config_param.json -maxdepth 0 -printf '%TY-%Tm-%Td %TH:%TM:%TS'",
                                         stdout=subprocess.PIPE, shell=True).communicate()[0]).split("'")[1].split(".")[0]

    # Check the last modified time
    cursor.execute("SELECT modTime FROM modification ORDER BY id DESC LIMIT 1")
    last_mod_time = cursor.fetchone()

    if last_mod_time is None:
        # No data in the table
        sql = "INSERT INTO modification (property, modTime, ram_min, ram_amber, cpu_min, cpu_amber, hdd_min, hdd_amber) VALUES ('config_log.json', '" + file_mod_time + "', '" + str(mem_config_level_min) + "', '" + str(mem_config_level_medium) + "', '" + str(cpu_config_level_min) + "','" + str(cpu_config_level_medium) + "', '" + str(hdd_config_level_min) + "', '" + str(hdd_config_level_medium) + "');"
        cursor.execute(sql)
        db.autocommit("modification")
    else:
        # Check weather the file is modified in the later date
        file_mod_time = datetime.strptime(file_mod_time, '%Y-%m-%d %H:%M:%S')
        last_mod_time = datetime.strptime(last_mod_time[0], '%Y-%m-%d %H:%M:%S')

        if last_mod_time < file_mod_time:
            # File has been modified, add the data
            sql = "INSERT INTO modification (property, modTime, ram_min, ram_amber, cpu_min, cpu_amber, hdd_min, hdd_amber) VALUES ('config_log.json', '" + str(file_mod_time) + "', '" + str(
                mem_config_level_min) + "', '" + str(mem_config_level_medium) + "', '" + str(
                cpu_config_level_min) + "','" + str(cpu_config_level_medium) + "', '" + str(
                hdd_config_level_min) + "', '" + str(hdd_config_level_medium) + "');"

            cursor.execute(sql)
            db.autocommit("modification")
        else:
            print("No File Modifications detected")

    # print(last_mod_time)
    # print(file_mod_time)


def check_mysql_status():
    return True


def check_telnet_status():
    return True


def get_server_name():
    svr_name = str(subprocess.Popen("hostname", stdout=subprocess.PIPE, shell=True).communicate()[0])
    server_ip = str(subprocess.Popen("hostname -i", stdout=subprocess.PIPE, shell=True).communicate()[0])

    return svr_name.split("'")[1].rsplit("\\n")[0] + " " + server_ip.split("'")[1].rsplit("\\n")[0]


def read_file():
    try:
        file = open("check_log.json", "r+")
        return file
    except FileNotFoundError:
        print("Log File not found")
        print("File will be created")
        open("check_log.json", 'w').close()
        read_file()


def close_file(file):
    try:
        file.close()
    except FileNotFoundError:
        print("Check_log not found")


web_hook = False
# Main functionality
while True:
    # server_name = get_server_name()
    # ram_utilization = check_ram_utilization_level()
    # cpu_utilization = check_cpu_utilization_level()
    # hdd_utilization = check_hdd_utilization_level()
    # mysql_connection = check_mysql_status()
    # telnet_connection = check_telnet_status()
    #
    # check_file = read_file()
    # data_array = {"Server_Name": server_name,
    #               "ram_util": ram_utilization,
    #               "cpu_util": cpu_utilization,
    #               "hdd_util": hdd_utilization,
    #               "mysql_con": mysql_connection,
    #               "telnet_con": telnet_connection}
    #
    # json.dump(data_array, check_file)
    #
    # close_file(check_file)

    check_file_modification_time()
    break
