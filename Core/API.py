from enum import Enum, auto
import logging
import json


class Service:
    def __init__(self) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)

    def GetLogger(self) -> logging.Logger:
        return self._logger
    
    async def DayTimeEvent(self):
        pass
    
    async def HourTimeEvent(self):
        pass

    async def start(self):
        pass
    
    async def run(self):
        pass

    async def stop(self):
        pass



class KeyBoard:
    class ButtonColor:
        blue = "primary"
        base = "secondary"
        red = "negative"
        green = "positive"

    class ButtonType:
        text = "text"
        open_link = "open_link"
        callback = "callback"
   
        
    def addButton(self, label:str, color:ButtonColor = ButtonColor.base, buttontype:ButtonType = ButtonType.text, payload:dict = None, link:str = None):
        pass

    def addLine(self):
        pass
    
class KeyBoardEmpty:
    pass
        

class EventType(Enum):
    Unknown = auto()
    NewMessage = auto()
    ReplyMessage = auto()
    KeyBoardEvent = auto()
    
class Event:
    def KeyBoard(self, one_time = True, inline = False) -> KeyBoard:    
        return None

        
    def GetSourse(self):
        return None

    def GetNameSourse(self) -> str:
        return "Undefined" 

    def GetEventType(self) -> EventType:
         return EventType.Unknown
     
    def GetMessage(self) -> str:
         return ""
    
    def GetMessageID(self) -> int:
        return 0

    def GetUserID(self) -> int:
        return None
    
 
    def GetAttachment(self) -> list[dict]:
        pass
 
    async def GetUserName(self) -> str:
        return ""

    def GetKeyBoardEvent(self) -> dict:
        return {}
    
    async def EditKeyBoardMessage(self, text:str, keyboard:KeyBoard = None):
        pass
    
    async def SendKeyBoardAnswer(self, data:str = None):
        pass
    
    async def SendMessage(self, text:str, keyboard:KeyBoard = None, reply:bool = False) -> int:
        pass
    
    
    async def SendFile(self, doc_file:str|bytes, filename:str = None):
        pass
    
    async def SetActive(self):
        pass 