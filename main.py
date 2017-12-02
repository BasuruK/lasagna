import os
import subprocess
from lasagna import RAG
from lasagna.log_manager import log, ERROR, LOGS
import json
import webbrowser
import MySQLdb
from datetime import datetime

# Open Config Files
try:
    with open("config_param.json", "r") as f:
        config_file = json.load(f)
except FileNotFoundError:
    log("config_param.json file does not exist", ERROR)

# Connect to the Database
try:
    db = MySQLdb.connect(config_file["mysql_hostname"],
                         config_file["mysql_uname"],
                         config_file["mysql_pass"],
                         config_file["mysql_dbname"])
    cursor = db.cursor()
except MySQLdb.DatabaseError:
    log("Database Not initialized, Please create a Database from the name mentioned in the config_param.json file", ERROR)
    exit(1)


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

# Admin Email
admin_email = config_file["notification_email"]


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
        sql = "INSERT INTO modification (property, modTime, ram_min, ram_amber, cpu_min, cpu_amber, hdd_min, hdd_amber) VALUES ('config_log.json', '" + file_mod_time + "', '" + str(
            mem_config_level_min) + "', '" + str(mem_config_level_medium) + "', '" + str(
            cpu_config_level_min) + "','" + str(cpu_config_level_medium) + "', '" + str(
            hdd_config_level_min) + "', '" + str(hdd_config_level_medium) + "');"
        cursor.execute(sql)
        db.autocommit("modification")
    else:
        # Check weather the file is modified in the later date
        file_mod_time = datetime.strptime(file_mod_time, '%Y-%m-%d %H:%M:%S')
        last_mod_time = datetime.strptime(last_mod_time[0], '%Y-%m-%d %H:%M:%S')

        if last_mod_time < file_mod_time:
            # File has been modified, add the data
            sql = "INSERT INTO modification (property, modTime, ram_min, ram_amber, cpu_min, cpu_amber, hdd_min, hdd_amber) VALUES ('config_log.json', '" + str(
                file_mod_time) + "', '" + str(
                mem_config_level_min) + "', '" + str(mem_config_level_medium) + "', '" + str(
                cpu_config_level_min) + "','" + str(cpu_config_level_medium) + "', '" + str(
                hdd_config_level_min) + "', '" + str(hdd_config_level_medium) + "');"

            cursor.execute(sql)
            db.autocommit("modification")

            # Return new modified time
            cursor.execute("SELECT * FROM modification ORDER BY id DESC LIMIT 1")
            new_mod_time = cursor.fetchone()
            return new_mod_time
        else:
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
    elif no_threads <= threads_connected:
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
    port = int(
        str(subprocess.Popen("nc -z 127.0.0.1 22; echo $?", stdout=subprocess.PIPE, shell=True).communicate()[0]).split(
            "\\n")[0].split("'")[1])
    if port == 1:
        # Port is closed
        return RAG.RED
    elif port == 0:
        # Port is closed
        return RAG.GREEN


def get_server_name():
    """
    Gets the Hostname and Host IP of the server
    :return: Hostname and Host IP
    """
    svr_name = str(subprocess.Popen("hostname", stdout=subprocess.PIPE, shell=True).communicate()[0])
    server_ip = str(subprocess.Popen("hostname -i", stdout=subprocess.PIPE, shell=True).communicate()[0])

    return svr_name.split("'")[1].rsplit("\\n")[0] + " " + server_ip.split("'")[1].rsplit("\\n")[0]


def read_html_file():
    """
    opens the html file, if not exists, create new file
    :return: File pointer to the HTML file
    """
    try:
        page_fp = open("webapp/webapp.html", 'r+')
        return page_fp
    except FileNotFoundError:
        log("HTML File not found, new file will be created", ERROR)
        print("HTML file not found, new file will be created")
        open("webapp/webapp.html", 'w').close()
        return read_html_file()


def close_html_file(file):
    try:
        file.close()
    except TypeError:
        pass


def truncate_html_file():
    open("webapp/webapp.html", 'w').close()


def format_html_page():
    """
    Format an HTML Page from the input data
    """
    html_format_header = """<!DOCTYPE html>
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
            tr{
                text-align: center;
            }
        </style>
    </head>
    <body>
    <script>
        $(document).ready(function () {
            var ram_util = $('#ram_util').text();
            var cpu_util = $('#cpu_util').text();
            var hdd_util = $('#hdd_util').text();
            var mysql_t_stat = $('#mysql_util').text();
            var mysql_opn_stat = $('#open_table').text();
            var telnet_stat = $('#tel_net').text();

            colorProfiler(['#ram_util','#cpu_util', '#hdd_util', '#mysql_util', '#open_table', '#tel_net'],[ram_util, cpu_util, hdd_util, mysql_t_stat, mysql_opn_stat, telnet_stat]);

            function colorProfiler(ids, vals){
                var length = ids.length;

                for(var i = 0; i < length; i++){
                    if(vals[i] === "GREEN"){
                        $(ids[i]).css('background-color','green');
                    }
                    else if (vals[i] === "AMBER"){
                        $(ids[i]).css('background-color','orange');
                    }
                    else if (vals[i] === "RED"){
                        $(ids[i]).css('background-color','red');
                    }
                }
            }
        })
    </script>
        """

    html_format_footer = """
    </body>
</html>
    """
    return html_format_header, html_format_footer


def html_body_data_parser(server_name, ram_util, cpu_util, hdd_util, mysql_t_stat, mysql_opn_tbl_stat, telnet_stat,
                          file_mod_stat):
    """
    Create HTML Page with the data recived
    :param server_name: Name of the server
    :param ram_util: Ram RAG Status
    :param cpu_util: CPU RAG Status
    :param hdd_util: HDD RAG Status
    :param mysql_t_stat: MySQL Threads Connected RAG Status
    :param mysql_opn_tbl_stat: MySQL Open Tables RAG Status
    :param telnet_stat: Telnet RAG Status
    :param file_mod_stat: File Modification data
    :return:
    """
    modifications_table = None

    html_body = """
    <table id="utilization" border="1|0" class="table table-striped table-dark">

        <tr>
            <th scope="col" colspan="3">Server Name</th>
            <th scope="col" colspan="2">Ram Utilization</th>
            <th scope="col" colspan="2">CPU Utilization</th>
            <th scope="col" colspan="2">HDD Utilization</th>
            <th scope="col" colspan="2">MYSQL Threads Status</th>
            <th scope="col" colspan=2">MYSQL Open Table Status</th>
            <th scope="col" colspan="2">Telnet Connection Status</th>
        </tr>
        <tr>\n
    """

    html_body += "<td colspan='3' id='server_name'>" + server_name + "</td>\n"
    html_body += "<td colspan='2' id='ram_util'>" + str(ram_util) + "</td>\n"
    html_body += "<td colspan='2' id='cpu_util'>" + str(cpu_util) + "</td>\n"
    html_body += "<td colspan='2' id='hdd_util'>" + str(hdd_util) + "</td>\n"
    html_body += "<td colspan='2' id='mysql_util'>" + str(mysql_t_stat) + "</td>\n"
    html_body += "<td colspan='2' id='open_table'>" + str(mysql_opn_tbl_stat) + "</td>\n"
    html_body += "<td colspan='2' id='tel_net'>" + str(telnet_stat) + "</td>\n"

    html_body += """</tr>\n
    </table>\n
    """

    if file_mod_stat is not None:
        file_mod_table_header = """
        <h3>Configuration parameters changed at the previous moment</h3>\n
        <table id="file_mod" border="1|0" class="table table-striped table-dark">
        <tr>
            <th scope="col" colspan="5">File Name</th>
            <th scope="col" colspan="2">Modfied Time Name</th>
            <th scope="col" colspan="2">Minimum Ram Level</th>
            <th scope="col" colspan="2">Amber Ram Level</th>
            <th scope="col" colspan="2">Minimum CPU Level</th>
            <th scope="col" colspan="2">Amber CPU Level</th>
            <th scope="col" colspan="2">Min HDD Level</th>
            <th scope="col" colspan="2">Amber HDD Level</th>
        </tr>
        <tr>
        """

        file_mod_table_body = "<td colspan='5' id='file_name'>" + str(file_mod_stat[1]) + "</td>\n"
        file_mod_table_body += "<td colspan='2' id='modtime'>" + str(file_mod_stat[2]) + "</td>\n"
        file_mod_table_body += "<td colspan='2' id='min_ram'>" + str(file_mod_stat[3]) + "</td>\n"
        file_mod_table_body += "<td colspan='2' id='amber_ram'>" + str(file_mod_stat[4]) + "</td>\n"
        file_mod_table_body += "<td colspan='2' id='min_cpu'>" + str(file_mod_stat[5]) + "</td>\n"
        file_mod_table_body += "<td colspan='2' id='amber_cpu'>" + str(file_mod_stat[6]) + "</td>\n"
        file_mod_table_body += "<td colspan='2' id='min_hdd'>" + str(file_mod_stat[7]) + "</td>\n"
        file_mod_table_body += "<td colspan='2' id='amber_hdd'>" + str(file_mod_stat[7]) + "</td>\n"

        file_mod_table_footer = """</tr>\n
        </table>\n"""

        modifications_table = file_mod_table_header + file_mod_table_body + file_mod_table_footer

    # get the header and footer content
    header, footer = format_html_page()
    # Make the final page
    if file_mod_stat is not None:
        html_page = header + html_body + str(modifications_table) + footer
        log("config_param.json File modification detected", LOGS)
    else:
        html_page = header + html_body + footer

    # Save the html page
    page_fp = read_html_file()
    truncate_html_file()
    page_fp.write(html_page)
    close_html_file(page_fp)

    log("HTML Page successfully created", LOGS)
    return html_page


def send_email(html_template, ram_util, cpu_util, hdd_util, mysql_t_stat, mysql_opn_tbl_stat, telnet_stat):
    """
    Send an E-mail with the RAG status of every feature
    :param html_template:
    :param ram_util:
    :param cpu_util:
    :param hdd_util:
    :param mysql_t_stat:
    :param mysql_opn_tbl_stat:
    :param telnet_stat:
    :return:
    """
    subject_line = ""

    data_array = {"ram_utilization": ram_util, "cpu_utilization": cpu_util,
                  "hdd_utilization": hdd_util, "mysql_threads_connected_status": mysql_t_stat,
                  "mysql_opn_tbl_status": mysql_opn_tbl_stat, "telnet_status": telnet_stat}

    for (key, value) in data_array.items():
        if value is "RED":
            subject_line += " RED " + str(datetime.now()) + " " + str(key)

    try:
        mail = subprocess.Popen('mail -s "$(echo "' + subject_line + '\nContent-Type: text/html")" ' + admin_email + ' < ' + os.path.abspath("webapp/webapp.html") + '', stdout=subprocess.PIPE, shell=True)
        log("Email Sent to address " + admin_email, LOGS)
    except FileNotFoundError:
        log("Email not sent, HTML file not found", ERROR)


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

    template = html_body_data_parser(server_name=server_name,
                                     ram_util=ram_utilization,
                                     cpu_util=cpu_utilization,
                                     hdd_util=hdd_utilization,
                                     mysql_t_stat=mysql_threads_active,
                                     mysql_opn_tbl_stat=mysql_open_tables,
                                     telnet_stat=telnet_connection,
                                     file_mod_stat=check_file_modification_time())

    send_email(template, ram_utilization, cpu_utilization, hdd_utilization, mysql_threads_active, telnet_connection,
               mysql_open_tables)
    break
