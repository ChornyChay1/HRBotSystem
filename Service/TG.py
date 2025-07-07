import json
import telegram
import collections
from Core.API import Service, Event, EventType, KeyBoard, KeyBoardEmpty
from Utill.FSM import FSM, FSMHandler


class TG(Service):
    def __init__(self, settings, path_strategy, fabric) -> None:
        super().__init__()
        self._setting = settings
        self._fsm = FSMHandler(path_strategy, parent_service= self, logger=self._logger, fabric=fabric)
        


    async def start(self):
        self._bot = telegram.Bot(self._setting.get("access_token"))
        self._logger.info("Start")
        pass

    async def run(self):
        async with self._bot:
            last_id = 0
            while True:
                try:

                    event: tuple[telegram.Update] = await self._bot.get_updates(timeout = 60, offset = last_id+1) #allowed_updates =  telegram.Update.ALL_TYPES
                except Exception as e:
                    self._logger.warn(f"TG error {str(type(e))}")
                    continue                

                for sub_event in event:
                    last_id = sub_event.update_id
                   
              
                    # print(sub_event)
                    
                    chat_id = 0
                    if sub_event.message:
                        chat_id = sub_event.message.chat_id
                    elif sub_event.callback_query:
                        chat_id = sub_event.callback_query.message.chat_id
                    else:
                        continue
                    
                    

                    fsm = await self._fsm.GetFSM(str(chat_id))
                    if fsm: 
                         await fsm(event = EventTG(self, sub_event, chat_id))




    async def HourTimeEvent(self):
        await self._fsm.UnloadNotWork()
                     
    async def SendMessage(self, peer_id:int, message:str, keyboard:KeyBoard = None, reply:Event = None) -> int:
        if type(keyboard) is KeyBoardTG:
            keyboard = keyboard.get()
        elif type(keyboard) is KeyBoardEmpty:
            keyboard = telegram.ReplyKeyboardRemove()
        else:
            keyboard = None

   
        
        try:
            result = await self._bot.send_message(chat_id = peer_id, text=message, reply_markup=keyboard)
            self._logger.debug(f"SendMessage to \"{peer_id}\"")
        except Exception as e:
            self._logger.warning(f"SendMessage error \"{type(e)}\"")
        pass
    
    async def DeleteMessage(self, peer_id:int, message_id:int):
         try:
            await self._bot.delete_message(chat_id = peer_id, message_id = message_id )
            self._logger.debug(f"DeleteMessage from \"{peer_id}\"") 
         except Exception as e:
            self._logger.warning(f"DeleteMessage error \"{type(e)}\"")
    

    async def stop(self):
        await self._fsm.stop()
        pass
         

class KeyBoardTG(KeyBoard):
       def __init__(self, one_time = True, inline = False):
           self._one_time = one_time
           self._inline = inline
           self._keyboard = [[]]
    
       def addButton(self, label:str, color:KeyBoard.ButtonColor = KeyBoard.ButtonColor.base, buttontype:KeyBoard.ButtonType = KeyBoard.ButtonType.text, payload:dict = None, link:str = None):
            if self._inline:
                self._keyboard[-1].append(telegram.InlineKeyboardButton(text=label, callback_data=json.dumps(payload)))
            else:
                self._keyboard[-1].append(telegram.KeyboardButton(text=label))
                
   
       def addLine(self):
            self._keyboard.append([])
            
       def get(self):
           if self._inline:
               return telegram.InlineKeyboardMarkup(self._keyboard)
           else: 
               return telegram.ReplyKeyboardMarkup(self._keyboard, one_time_keyboard=self._one_time,resize_keyboard=True)
        


class EventTG(Event):
    def __init__(self, tg:TG, event: telegram.Update, peer_id):
        self._event = event
        self._tg = tg
        self._peer_id = peer_id
        self._bot_mes_id = None

    def KeyBoard(self, one_time = True, inline = False) -> KeyBoard:    
        return KeyBoardTG(one_time=one_time, inline=inline)

    def GetNameSourse(self) -> str:
        return "TG" 
    
    def GetSourse(self) -> TG:
        return self._tg

    def GetEventType(self) -> EventType:
        if self._event.message:
            return EventType.NewMessage
        if self._event.callback_query:
            return EventType.KeyBoardEvent
        
        return EventType.Unknown
     
    def GetMessage(self) -> str:
        if not self._event.message:
            return None
        
        return self._event.message.text

    def GetMessageID(self) -> int:
        if self._event.message:
            return self._event.message.message_id
        if self._event.callback_query:
            return self._event.callback_query.message.message_id
        
        return 0

    def GetUserID(self) -> int:
        if self._event.message:
            return self._event.message.from_user.id

        if self._event.callback_query:
            return self._event.callback_query.from_user.id
        
        return 0
    
    #переделать
    def GetAttachment(self) -> list[dict]:
        if not self._event.message:
            return None


        if self._event.message.photo:
            return self._event.message.photo      
        if self._event.message.sticker:
            return self._event.message.sticker
        if self._event.message.audio:
            return self._event.message.audio
        if self._event.message.video:
            return self._event.message.video
        

        return None
        pass 
    
    #под вопрос
    async def GetUserName(self) -> str:
        if self._event.message:
            return "@" + str(self._event.message.from_user.username)        
        if self._event.callback_query:
            return "@" + str(self._event.callback_query.from_user.username)       

        return ""

    def GetKeyBoardEvent(self) -> dict:
        if self._event.callback_query:
           return json.loads(self._event.callback_query.data)
        
        return {}
    
    async def SendKeyBoardAnswer(self, data:str = None):
        if self._event.callback_query:
            await self._event.callback_query.answer()
        pass
    
    async def EditKeyBoardMessage(self, text:str, keyboard:KeyBoard = None) ->int:
        if self._event.callback_query: 
            if type(keyboard) is KeyBoardTG:
                keyboard = keyboard.get()
            elif type(keyboard) is KeyBoardEmpty:
                keyboard = telegram.ReplyKeyboardRemove()
            else:
                keyboard = None
                

            
            try:
                await self._event.callback_query.message.edit_text(text=text, reply_markup=keyboard)
                self._tg._logger.debug(f"EditKeyBoardMessage to \"{self._peer_id}\"")   
                return self._event.callback_query.message.message_id

            except Exception as e:
                self._tg._logger.warning(f"EditKeyBoardMessage to \"{self._peer_id}\" error \"{type(e)}\"")   
        
    
    async def SendMessage(self, text:str, keyboard:KeyBoard = None, reply:bool = False) -> int:  
        if type(keyboard) is KeyBoardTG:
            keyboard = keyboard.get()
        elif type(keyboard) is KeyBoardEmpty:
            keyboard = telegram.ReplyKeyboardRemove()
        else:
            keyboard = None
            
       
        self._tg._logger.debug(f"SendMessage to \"{self._peer_id}\"")
        try:
            result:telegram.Message = await self._event._bot.send_message(chat_id = self._peer_id, text=text, reply_markup=keyboard)
            return result.message_id
        except Exception as e:
            print(e)
        pass
    
    async def SendFile(self, doc_file:str|bytes, filename:str = None):
         self._tg._logger.debug(f"SendFile to \"{self._peer_id}\"") 
         try: 
            await self._event._bot.send_document(chat_id = self._peer_id,document = doc_file, filename = filename)
         except Exception as e:
            print(e)

    async def SetActive(self):
        pass

