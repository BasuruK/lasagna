"""
LOGGER:- used to log changes to the system and the errors
"""


def open_file():
    """
    :return: File pointer to the log file
    """
    try:
        log_file = open("log.txt", 'a+')
        return log_file
    except FileNotFoundError:
        print("Log file not found")
        pass


def close_file(file):
    """
    Close the file pointer
    :param file: File pointer
    :return: None
    """
    file.close()


def log(message, type="log"):
    """
    :param message: the log message
    :param type: Error / Normal [ERR/ LOG]
    :return: None
    """
    log_file = open_file()
    log_file.write(type + ": " + message)
