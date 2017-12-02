import os
import subprocess
from lasagna import RAG
from lasagna import log_manager
import json
import webbrowser
import MySQLdb
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

# MySQL Threads
threads_connected = config_file["threads_connected"]

# MySQL open tables limit Status
open_tables = config_file["open_tables"]


def check_ram_utilization_level():
    """
    Based on the utilization configuration level update the RAG status for Ram
    :return: RAG Status
    """
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
    """
    Based on the utilization configuration level update the RAG status for CPU
    :return: RAG Status
    """
    cpu_util = subprocess.Popen("mpstat | awk -F ' ' '{print $12}'", stdout=subprocess.PIPE, shell=True)
    cpu_util = float(str(cpu_util.communicate()[0]).split("\\n")[3])

    if cpu_util <= cpu_config_level_min:
        return RAG.RED
    elif cpu_config_level_medium <= cpu_util <= cpu_config_level_min:
        return RAG.AMBER
    elif cpu_util > cpu_config_level_medium:
        return RAG.GREEN


def check_hdd_utilization_level():
    """
    Based on the utilization configuration level update the RAG status for HDD
    :return: RAG Status
    """
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
    """
    Check the config_param.json file's modification time, and if the file has been modified previously then update
    the database record based for the new modified time.
    :return: Last modified time | None
    """
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

            # Return new modified time
            cursor.execute("SELECT modTime FROM modification ORDER BY id DESC LIMIT 1")
            new_mod_time = cursor.fetchone()
            return new_mod_time
        else:
            print("No File Modifications detected")
            return None


def check_mysql_thread_status():
    """
    Check 'Threads_connected' MySQL parameter against the configurable level
    :return: RAG Status
    """
    cursor.execute("SHOW STATUS LIKE 'Threads_Connected'")
    no_threads = cursor.fetchone()
    no_threads = int(no_threads[1])

    if no_threads > threads_connected:
        return RAG.RED
    elif no_threads < threads_connected:
        return RAG.GREEN


def check_mysql_open_tables_status():
    """
    Check 'Open_tables' MySQL parameter against the configurable level
    :return: RAG Status
    """
    cursor.execute("SHOW STATUS LIKE 'Open_tables'")
    tables = int(cursor.fetchone()[1])

    if tables > open_tables:
        return RAG.RED
    elif tables < open_tables:
        return RAG.GREEN


def check_telnet_status():
    """
    Check Telnet status of the server
    :return: True if port is open and accepting connections | False if otherwise
    """
    port = str(subprocess.Popen("nc -z 127.0.0.1 22; echo $?", stdout=subprocess.PIPE, shell=True).communicate()[0]).split("\\n")[0].split("'")[1]
    if port == 1:
        # Port is closed
        return False
    elif port == 0:
        # Port is closed
        return True


def get_server_name():
    """
    Gets the Hostname and Host IP of the server
    :return: Hostname and Host IP
    """
    svr_name = str(subprocess.Popen("hostname", stdout=subprocess.PIPE, shell=True).communicate()[0])
    server_ip = str(subprocess.Popen("hostname -i", stdout=subprocess.PIPE, shell=True).communicate()[0])

    return svr_name.split("'")[1].rsplit("\\n")[0] + " " + server_ip.split("'")[1].rsplit("\\n")[0]


def read_file():
    """
    Open the 'check_log.json' file for reading
    :return: File pointer
    """
    try:
        file = open("check_log.json", "r+")
        return file
    except FileNotFoundError:
        print("Log File not found")
        print("File will be created")
        open("check_log.json", 'w').close()
        read_file()


def close_file(file):
    """
    Close the file
    :param file: file pointer
    """
    try:
        file.close()
    except FileNotFoundError:
        print("Check_log not found")


def format_html_page(body_data):
    """
    Format an HTML Page from the input data
    :param body_data: Table data displayed in the middle
    """
    html_format_header = """
        <!DOCTYPE html>
    <html lang="en">
    <meta charset="UTF-8">
    <title>Information Monitor</title>

    <head>
        <!--Load jQuery-->
        <script
                src="https://code.jquery.com/jquery-3.2.1.js"
                integrity="sha256-DZAnKJ/6XZ9si04Hgrsxu/8s717jcIzLy3oi35EouyE="
                crossorigin="anonymous">
        </script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.12.3/umd/popper.min.js"
                integrity="sha384-vFJXuSJphROIrBnz7yo7oB41mKfc8JzQZiCq4NCceLEaO4IHwicKwpJf9c9IpFgh"
                crossorigin="anonymous">
        </script>
        <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0-beta.2/js/bootstrap.min.js"
                integrity="sha384-alpBpkh1PFOepccYVYDB4do5UnbKysX5WZXm3XxPqe5iKTfUKjNkCk9SaVuEZflJ"
                crossorigin="anonymous">
        </script>

        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0-beta.2/css/bootstrap.min.css"
              integrity="sha384-PsH8R72JQ3SOdhVi3uxftmaW6Vc51MKb0q5P2rRUpPvrszuE4W1povHYgTpBfshb"
              crossorigin="anonymous">

        <style>
            td{
                text-align: center;
            }
        </style>
    </head>
    <body>
        """

    html_format_footer = """
    </body>
</html>
    """
    

web_hook = False
# Main functionality
while True:
    server_name = get_server_name()
    ram_utilization = check_ram_utilization_level()
    cpu_utilization = check_cpu_utilization_level()
    hdd_utilization = check_hdd_utilization_level()
    mysql_threads_active = check_mysql_thread_status()
    telnet_connection = check_telnet_status()
    mysql_open_tables = check_mysql_open_tables_status()

    check_file = read_file()
    data_array = {"Server_Name": server_name,
                  "ram_util": ram_utilization,
                  "cpu_util": cpu_utilization,
                  "hdd_util": hdd_utilization,
                  "mysql_con": mysql_threads_active,
                  "telnet_con": telnet_connection}

    json.dump(data_array, check_file)

    close_file(check_file)

    check_file_modification_time()


    break
