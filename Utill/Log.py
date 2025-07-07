from datetime import datetime
from typing import Any
from logging import LogRecord, Handler


class BCOLOR:


    RESET = '\033[0m'

    TIME = '\033[32m'
    SERVICE = '\033[36m'


    DEBUG = '\033[34;1m'
    INFO = '\033[37m'
    WARN = '\033[33m'
    ERROR = '\033[31m'
    FATAL = '\033[31;4;1m'
    UNDEF = '\033[31;1m'
    
    
class LOGLEVEL:
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    FATAL = 50




class LogHandler(Handler):
    def _level2msg(self, level: int):
        if level == LOGLEVEL.DEBUG:
            return '[DEBUG] ', BCOLOR.DEBUG
        
        if level == LOGLEVEL.INFO:
            return '[INFO] ', BCOLOR.INFO
        
        if level == LOGLEVEL.WARN:
            return '[WARN] ', BCOLOR.WARN
        
        if level == LOGLEVEL.ERROR:
            return '[ERROR] ', BCOLOR.ERROR
        
        if level == LOGLEVEL.FATAL:
            return '[FATAL] ', BCOLOR.FATAL
        
        return '[UNDEF] ', BCOLOR.UNDEF


    def emit(self, record: LogRecord) -> None:

        # print("name",record.name)
        # print("message",record.getMessage())
        # print("threadName",record.threadName)
        # print("filename",record.filename)
        # print("levelname",record.levelname)
        # print("module",record.module)
        # print("thread",record.thread)
        # print("funcName",record.funcName)
        # print("lineno",record.lineno)
        # print("levelno",record.levelno)

        # return

        current_datetime = datetime.now()    
        time_str = "[" +  (str)(current_datetime.day).zfill(2) + "." + (str)(current_datetime.month).zfill(2) + "." + (str)(current_datetime.year).zfill(2) + " " + (str)(current_datetime.hour).zfill(2) + ":" + (str)(current_datetime.minute).zfill(2) + ":" + (str)(current_datetime.second).zfill(2) + "] "
        
        service = "[" + record.name + "] "
        levelmsg = self._level2msg(record.levelno)

        print(BCOLOR.TIME + time_str + BCOLOR.SERVICE + service + levelmsg[1] + levelmsg[0] + record.getMessage() + BCOLOR.RESET)

    