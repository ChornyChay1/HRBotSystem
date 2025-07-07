import os
import json
from random import randint


import aiovk
import aiovk.longpoll

from Core.API import KeyBoardEmpty, Service, Event, EventType, KeyBoard
from Utill.FSM import FSM, FSMHandler




class VK(Service):
    def __init__(self, settings, path_strategy,fabric) -> None:
        super().__init__()
        self._setting = settings
        self._fsm = FSMHandler(path_strategy,  parent_service = self, logger=self._logger,fabric=fabric)
            

        


    async def start(self):
        self._session = aiovk.TokenSession(self._setting.get("access_token"))
        self._api = aiovk.API(self._session)
        self._longpoll = aiovk.longpoll.BotsLongPoll(self._api, self._setting.get("group_id"))
        self._logger.info("Start")

    async def run(self):
        while True:
            try:
                events = await self._longpoll.wait()
            except Exception as e:
                self._logger.critical(f"VK error {str(type(e))}")
                continue
        

            if events.get("updates"):
                for event in events.get("updates"):
                    if event.get("type") == "message_typing_state":
                        continue

                    if event.get("type") == "message_new" or event.get("type") == "message_event" or (event.get("type") == "message_reply"and event.get("object").get("from_id",-1) > 0):
                        if not event.get("object"): 
                            continue

                        peer_id = event.get("object").get("peer_id")
                            
                        fsm = await self._fsm.GetFSM(str(peer_id))
                        if fsm: 
                            await fsm(event = EventVK(self, peer_id, event))
                         


    async def HourTimeEvent(self):
         await self._fsm.UnloadNotWork()
                                
    async def SendMessage(self, message:str, peer_id:int, keyboard:KeyBoard = None, reply:Event = None):
        
        splt_string = _split_string(message)
        
        for msg in splt_string:
            send = {"peer_id": peer_id,"message":msg, "random_id": randint(0,10000000) }
            
            
            if keyboard and (msg == splt_string[-1]):
                if type(keyboard) is KeyBoardVK:
                    send["keyboard"] = keyboard.get()
                elif type(keyboard) is KeyBoardEmpty:
                    send["keyboard"] = json.dumps({"buttons":[]}) 
                

            if reply:
                if reply.GetEventType() is EventType.NewMessage:
                    obj = reply._event.get("object")
                    if obj:
                        conversation_message_id = obj.get("conversation_message_id")
                        if conversation_message_id: 
                            fwdmsg = {"peer_id": peer_id, "conversation_message_ids": conversation_message_id, "is_reply": 1}
                            send["forward"] = json.dumps(fwdmsg)
            try:
                self._logger.debug(f"SendMessage to \"{peer_id}\"")
                response = await self._api.messages.send(**send)
                # print(response)
            except Exception as e:
                self._logger.critical(f"SendMessgae exeption \"{e}\"")
                # print(e)
                pass

    async def SendKeyBoardAnswer(self,event_id:str, user_id:int, peer_id:int, event_text:str = None):
        send = {"peer_id": peer_id,"event_id":event_id, "user_id": user_id}
        
        if event_text:
            send["event_data"] = json.dumps({"type": "show_snackbar", "text": event_text})
            # print(send)
                    
        try:
            self._logger.debug(f"SendKeyBoardAnswer to \"{peer_id}\"")
            response = await self._api.messages.sendMessageEventAnswer(**send)
            # print(response)
        except Exception as e:
            self._logger.critical(f"SendKeyBoardAnswer exeption \"{e}\"")
            # print(e)
            pass
      
    async def GetUserName(self, user_id:int)->str:
        try: 
            result = await self._api.users.get(user_ids = user_id)
            return result[0]['first_name']
        except Exception as e:
            self._logger.critical(f"GetUserName exeption \"{e}\"")
            # print(e)
            pass
        
    async def SetActive(self, peer_id: int):
        send = {"peer_id": peer_id, "type": "typing"}
        try:
            await self._api.messages.setActivity(**send)
        except Exception as e:
            self._logger.critical(f"SetActive exeption \"{e}\"")
            # print(e)
            pass

    async def stop(self):
        await self._fsm.stop()
        await self._session.close()
        

class KeyBoardVK(KeyBoard):
    def __init__(self, one_time = True, inline = False):
        self._keyboard = {"inline": inline, "buttons":[[]]}
        
        if not inline:
            self._keyboard["one_time"] = one_time
            
    def addButton(self, label:str, color:KeyBoard.ButtonColor = KeyBoard.ButtonColor.base, buttontype:KeyBoard.ButtonType = KeyBoard.ButtonType.text, payload:dict = None, link:str = None):
        key = {}
        if buttontype == KeyBoard.ButtonType.text or buttontype == KeyBoard.ButtonType.callback:
            key["type"] = buttontype
            key["label"] = label
            if payload:
                key["payload"] = json.dumps(payload)


        self._keyboard["buttons"][-1].append({"action":key, "color": color})

    def addLine(self):
        self._keyboard["buttons"].append([])
        
    def get(self)->str:
        return json.dumps(self._keyboard)



class EventVK(Event):
    def __init__(self, vk:VK, peer_id:int, event):
        self._vk = vk
        self._event = event
        self._peer_id = peer_id
        
    def KeyBoard(self, one_time = True, inline = False) -> KeyBoard:    
        return KeyBoardVK(one_time=one_time, inline=inline)

          
    def GetSourse(self) -> VK:
        return self._vk    

    def GetNameSourse(self) -> str:
        return "VK"
        
    def GetEventType(self) -> EventType:
        event_type =  self._event.get("type")
        if event_type == "message_new":
            return EventType.NewMessage
        if event_type == "message_event":
            return EventType.KeyBoardEvent
        if event_type == "message_reply":
            return EventType.ReplyMessage
        return EventType.Unknown
       
    def GetUserID(self) -> int:
        if self._event.get("type") == "message_new": 
            obj = self._event.get("object")        
            return obj.get("from_id")

        if self._event.get("type") == "message_event": 
            obj = self._event.get("object")        
            return obj.get("user_id")

       
        return None

    def GetMessage(self) -> str:
        if self._event.get("type") == "message_new":
           if self._event.get("object"): 
               if self._event.get("object").get("text"):
                   return self._event.get("object").get("text")
        return None
    
    def GetAttachment(self) -> list[dict]:
        if self._event.get("type") == "message_new":
           return self._event.get("object", {}).get("attachments", None)
        return None
    
    async def GetUserName(self) -> str:
        user_id = self.GetUserID()
        if not user_id:
            return ""

        return await self._vk.GetUserName(user_id)
    
    def GetKeyBoardEvent(self) -> dict:
        if not self._event.get("type") == "message_event":
            return {}
        
        obj = self._event.get("object")
        if not obj:  
            return {}
        
        if not type(obj.get("payload")) is dict:
            return {}
        
        return obj.get("payload")
    
    async def SendKeyBoardAnswer(self, data:str = None):
        if self._event.get("type") == "message_event":
            obj = self._event.get("object")
            if obj: 
                await self._vk.SendKeyBoardAnswer(obj.get("event_id"), obj.get("user_id"), obj.get("peer_id"), data)
        pass

    async def SetActive(self):
        await self._vk.SetActive(peer_id = self._peer_id)

    async def SendMessage(self, text:str, keyboard:KeyBoard = None, reply:bool = False):
        if not ((type(keyboard) is KeyBoardVK) or (type(keyboard) is KeyBoardEmpty)):
            keyboard = None
            
    
            
        await self._vk.SendMessage(text, self._peer_id, keyboard=keyboard, reply=self if reply==True else None)
        

def _split_string(string):
    max_length = 3500
    if len(string) > max_length:
        return [string[i:i+max_length] for i in range(0, len(string), max_length)]
    else:
        return [string]