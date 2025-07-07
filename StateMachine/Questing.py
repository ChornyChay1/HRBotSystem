from Core.API import *
from Service.DB import DB
from Service.JSONQuestConvert import *
from Service.TG import TG
from Utill.FSM import FSM
import datetime

class Questing(FSM):
    def __init__(self, peer_id:int, s_dict: dict, report_peer_id) -> None:
        self._peer_id = peer_id
        self._s_dict = s_dict
        self._user = None
        self._reader: JSONQuestReader = self._s_dict["reader"]
        self._pull = None
        self._quest = None
        self._userID = None
        self._retry = False
        self._oldList = None
        self._report_peer_id = report_peer_id
        self.variant = None
        self._isRequest = None

        
        self.FirstSee = True
        
        self.tg: TG   = self._s_dict["TG"]
        self.Base: DB   = self._s_dict["BD"]
        super().__init__()
        


    async def ReplyChecker(self, event:Event) ->bool:
        if event.GetEventType() is EventType.ReplyMessage:
            await event.SendKeyBoardAnswer()
            keyboard = event.KeyBoard(one_time=False)
            keyboard.addButton("Перейти к работе с ботом",color= KeyBoard.ButtonColor.green, buttontype=KeyBoard.ButtonType.text, payload={"type": "First"})
            await event.SendMessage("⚠️Действие бота временно остановлено",keyboard=keyboard)  
            self._isRequest = False
            self.SetState(self.ManagerAnswerState)
            return True
        return False
    

  
            
    
      #спрашивает куда пойти       
    async def FirstState(self, event):
        #проверка если менеджер пишет
        if await self.ReplyChecker(event):
            return
        await event.SendKeyBoardAnswer()
        # #проверка если менеджер пишет
        # await self.ReplyChecker(event)
        
        keyboard = event.KeyBoard()
        #проверка на наличие в базе
        if self.FirstSee:
            self.FirstSee = False
            await event.SendMessage("Привет, рады видеть тебя здесь!🙂")
            

            self.userID = event.GetNameSourse() + str(self._peer_id)        


        if not await self.Base.searchField("UserID",self.userID):
            keyboard.addButton("Начать анкетирование",color= KeyBoard.ButtonColor.green, buttontype=KeyBoard.ButtonType.text, payload={"type": "Questing"})
            keyboard.addButton("Попросить обратную связь",color= KeyBoard.ButtonColor.blue, buttontype=KeyBoard.ButtonType.text, payload={"type": "WriteToManager"})

            self.SetState(self.FirstMenuState)
            await event.SendMessage("Вы можете начать анкетирование, нажав на соответствующую кнопку или же дать запрос на обратную связь",keyboard=keyboard)
        else:
            self._retry=True
            keyboard.addButton("Редактировать анкету",color= KeyBoard.ButtonColor.green, buttontype=KeyBoard.ButtonType.text, payload={"type": "Redacting"})
            keyboard.addButton("Попросить обратную связь",color= KeyBoard.ButtonColor.blue, buttontype=KeyBoard.ButtonType.text, payload={"type": "WriteToManager"})
            self.SetState(self.FirstMenuState)
            await event.SendMessage("Вы можете редактировать созданную Вами анкету, нажав на соответствующую кнопку или же дать запрос на обратную связь",keyboard=keyboard)
        

                  
    #обрабатывает ответ пользователя и отправляет в соответвующее состояние       
    async def FirstMenuState(self, event:Event):
        if await self.ReplyChecker(event):
            return
        if event.GetEventType() is EventType.NewMessage:
            if event.GetMessage() == "Начать анкетирование" or  event.GetMessage() == "Заполнить анкету":
                await event.SendKeyBoardAnswer()
                self.SetState(self.QuestingState)
                await event.SendMessage("Начнём анкетирование. Постарайтесь ответить как можно на большее количество вопросов, это поднимет Вас в рейтинге. Удачи 😉",keyboard=KeyBoardEmpty())
                self._pull = self._reader.getQuestPull()
                #вставим в answer list from
                my_dict = {"UserID": self.userID}
                self._pull.setAnswer(my_dict)
                self._pull.id-=1
                await self.QuestingSend(event)
                return


            elif event.GetMessage() == "Попросить обратную связь":
                await event.SendKeyBoardAnswer()
                keyboard = event.KeyBoard(one_time=False)

                if not self._isRequest:
                    if event.GetNameSourse() == "VK":
                        await self.tg.SendMessage(self._report_peer_id,f"Внимание! Пользователь в {event.GetNameSourse()} зовёт менеджера.Ссылка на пользователя: https://vk.com/id"+str(self._peer_id))
                    if event.GetNameSourse() == "TG":
                        await self.tg.SendMessage(self._report_peer_id,f"Внимание! Пользователь в {event.GetNameSourse()} зовёт менеджера.Ссылка на пользователя:t.me/"+str(await event.GetUserName()))
                    self._isRequest = True
                keyboard.addButton("Перейти к работе с ботом",color= KeyBoard.ButtonColor.green, buttontype=KeyBoard.ButtonType.text, payload={"type": "First"})
                await event.SendMessage("⚠️Запрос отправлен. Мы обязательно с Вами свяжемся!", keyboard=keyboard)
                self.SetState(self.ManagerAnswerState)
                return
            

            elif event.GetMessage() == "Редактировать анкету":
                await event.SendKeyBoardAnswer()
                keyboard = event.KeyBoard()
                await self.Repair(event)
                self._oldList = self._pull.getRawAnswerList()
                #в это месте уже должен быть заполнен пу
                keyboard.addButton("Показать мою анкету",color= KeyBoard.ButtonColor.blue, buttontype=KeyBoard.ButtonType.text, payload={"type": "CheckQuests"})
                keyboard.addButton("Заполнить анкету",color= KeyBoard.ButtonColor.green, buttontype=KeyBoard.ButtonType.text, payload={"type": "Questing"})
                await event.SendMessage("Пожалуйста, сделайте свой выбор:", keyboard=keyboard)
                return
            elif event.GetMessage() == "Показать мою анкету":
                await event.SendKeyBoardAnswer()
                await self.CheckAnswers(event,self._pull.getRawAnswerList())
                return
        await self.FirstState(event)
        return 
            

    #Отправляем вопрос формируем клавиатуру
    async def QuestingSend(self, event:Event):
        
        if await self.ReplyChecker(event):
            return

        #Мммм.. Время костылей!!!
        self._quest = self._pull.giveQuest()
        if self._quest is None: 
            await self.CorrectingState(event)
            return
        if self._quest.getQuestType() is QuestTypes.Social:
            if event.GetNameSourse() == "VK" and self._quest.getQuestColumb() == "VK":      
                my_dict = {"VK": "http://vk.com/id" + str(self._peer_id)}
                self._pull.setAnswer(my_dict)
                self._quest = self._pull.giveQuest()
                
            if event.GetNameSourse() == "TG" and self._quest.getQuestColumb() == "TG":
                my_dict = {"TG": "t.me/" + str(await event.GetUserName())}
                self._pull.setAnswer(my_dict)
                self._quest = self._pull.giveQuest()
                
      
        keyboard = event.KeyBoard()
        message = ""
        #если выбор
        if self._quest.getQuestType() is QuestTypes.Choice:
            i = 1
            for variant in self._quest.getQuestVar():
                if i%2 ==0:
                     self.variant = variant 
                     keyboard.addLine()
                keyboard.addButton(variant, buttontype=KeyBoard.ButtonType.text, payload={"type": "choice","variant": variant})
                i+=1
            keyboard.addLine() 
        if self._quest.questCanBeSkiped:
            keyboard.addButton("Пропустить",color= KeyBoard.ButtonColor.blue, buttontype=KeyBoard.ButtonType.text, payload={"type": "skip"})
            keyboard.addLine() 
        if self._retry and not self._oldList[self._quest.getQuestColumb()] == None:
            keyboard.addButton("Оставить прежнее значение",color= KeyBoard.ButtonColor.blue, buttontype=KeyBoard.ButtonType.text, payload={"type": "fix"})
            message = "\nПрежнее значение: \n" + str(self._oldList[self._quest.getQuestColumb()])
            
            keyboard.addLine()
        keyboard.addButton("Назад",color= KeyBoard.ButtonColor.red, buttontype=KeyBoard.ButtonType.text, payload={"type": "back"}) 
        await event.SendMessage(self._quest.getTextQuest() + message,keyboard=keyboard) 


        self.SetState(self.QuestingState)
         
    #Получаем ответ на вопрос
    async def QuestingState(self, event:Event):
        
        #проверка если менеджер пишет
        await self.ReplyChecker(event)


        if event.GetEventType() is EventType.NewMessage:
            try:
                if event.GetMessage() == "Оставить прежнее значение":
                     tmp =  str(self._oldList[self._quest.getQuestColumb()])
                     await event.SendMessage("☑️Оставлено прежнее значение: " + tmp,keyboard=KeyBoardEmpty() )
                     # self._quest.setRawAnswer(tmp)
                     self._quest.setAnswer(tmp)
                     await self.QuestingSend(event)
                     return
                elif event.GetMessage() == "Пропустить":
                    self._quest.skipQuest()
                    await event.SendMessage("➡️ Вопрос был пропущен",keyboard=KeyBoardEmpty() )
                    await self.QuestingSend(event)
                    return
                elif event.GetMessage() == "Назад":
                    if self._pull.id == 0:
                        await event.SendMessage("⬅️Давайте вернёмся назад: ",keyboard=KeyBoardEmpty() )
                        await self.FirstState(event)

                        return

                    else:
                        self._quest.backQuest() 
                        await event.SendMessage("⬅️Предыдущий вопрос: ",keyboard=KeyBoardEmpty() )
                        await self.QuestingSend(event)
                        return

                elif event.GetMessage() == None:
                    await event.SendMessage("⚠Ваш ответ некорректен",keyboard=KeyBoardEmpty() )
                    await self.QuestingSend(event)
                    return                        
                elif not self._quest.getQuestType() is QuestTypes.Choice:
                    pass
                elif event.GetMessage() in self._quest.getQuestVar():
                    self.variant = None
                elif not self._quest.getQuestType() is QuestTypes.Choice:
                    pass
                else:
                    await event.SendMessage("⚠Вы ввели неверный вариант",keyboard=KeyBoardEmpty() )
                    await self.QuestingSend(event)
                    return 

                self._quest.setAnswer(event.GetMessage())
            except JSONReaderExeptionGlobal as e:
                 await event.SendMessage(f"⚠ "+str(e))
            except Exception as e:
                await event.SendMessage("⚠Произошла неизвестная ошибка, обратитесь к администратору")
                
            await self.QuestingSend(event)
            
        # if event.GetEventType() is EventType.KeyBoardEvent:
        #     try:
        #         event.SendKeyBoardAnswer()
        #         if event.GetKeyBoardEvent().get("type") == "fix":
        #              tmp =  self._oldList[self._quest.getQuestColumb()]
        #              await event.SendMessage("Оставлено прежнее значение: " + str(tmp),keyboard=KeyBoardEmpty() )
        #              self._quest.setRawAnswer(tmp)
        #              self._quest.setAnswer(tmp)
        #         elif event.GetKeyBoardEvent().get("type") == "skip":
        #             self._quest.skipQuest()
        #             await event.SendMessage("➡️ Вопрос был пропущен",keyboard=KeyBoardEmpty() )
        #         elif event.GetKeyBoardEvent().get("type") == "back":
        #             if self._pull.id == 0:
        #                 await event.SendMessage("Предыдущее состояние: ",keyboard=KeyBoardEmpty() )
        #                 await self.FirstState(event)
        #                 return
        #             else:
        #                 self._quest.backQuest() 
        #                 await event.SendMessage("Предыдущий вопрос: ",keyboard=KeyBoardEmpty() )
        #         elif event.GetKeyBoardEvent().get("type") == "choice":
        #             self._quest.setAnswer(event.GetKeyBoardEvent()["variant"])
        #             await event.SendMessage("✅ Ваш ответ: "+ str(event.GetKeyBoardEvent()["variant"]),keyboard=KeyBoardEmpty() )
        #         else:
        #              await event.SendMessage("Ошибка обработки кнопки",keyboard=KeyBoardEmpty() )
        #     except JSONReaderExeptionGlobal as e:
        #          await event.SendMessage(str(e))
        #     except Exception as e:
        #         await event.SendMessage("Произошла неизвестная ошибка, обратитесь к администратору")
                
        #     await self.QuestingSend(event)
            
    
    #Проверяет закончено ли анкетирование, выводит анкету всю
    async def CorrectingState(self, event:Event):
       
        if await self.ReplyChecker(event):
            return
        self._quest = self._pull.giveQuest()
        if self._quest is None: 
            await event.SendMessage("Анкетирование закончено✅",keyboard=KeyBoardEmpty()) 
            await event.SendMessage("Пожалуйста, сверьте вопросы со своими ответами: \n") 
            #вот тут вывод 100 процентов нужно модернизировать будет
            await self.CheckAnswers(event,self._pull.getRawAnswerList())
            return
        await event.SendMessage(self._quest.getTextQuest(),keyboard=KeyBoardEmpty()) 
        
        
    #После нажатия на кнопку вернуться к работе с ботом
    async def ManagerAnswerState(self, event:Event):
        
        if event.GetMessage() == "Перейти к работе с ботом":
                await event.SendKeyBoardAnswer()
                await event.SendMessage("☑️Возвращаемся к работе с ботом",keyboard=KeyBoardEmpty())
                await self.FirstState(event)
                return
        return
       
        
            
    #После нажатия на кнопку вернуться к работе с ботом
    async def FinaleState(self, event:Event):
        if await self.ReplyChecker(event):
            return
        elif event.GetMessage() == "Все верно, отправить":
                await event.SendKeyBoardAnswer()
                await self.Base.upsertData("UserID",self.userID,self._pull.getAnswers()) 
                if not self._retry:
                    if event.GetNameSourse() == "VK":
                        await self.tg.SendMessage(self._report_peer_id,f"Внимание! Пользователь в {event.GetNameSourse()} заполнил анкету.Ссылка на пользователя: https://vk.com/id"+str(self._peer_id) + "\nСодержание анкеты:\n" + await self.GetCheckMessage(self._pull.getRawAnswerList()))
                    if event.GetNameSourse() == "TG":
                        await self.tg.SendMessage(self._report_peer_id,f"Внимание! Пользователь в {event.GetNameSourse()} заполнил анкету.Ссылка на пользователя: t.me/"+str(await event.GetUserName()) + "\nСодержание анкеты:\n" + await self.GetCheckMessage(self._pull.getRawAnswerList()))
                await event.SendMessage("✅Ваши данные успешно отправлены! ",keyboard=KeyBoardEmpty())
                await self.FirstState(event)
                return
        elif event.GetMessage() == "Заполнить заново" :
                await event.SendKeyBoardAnswer()
                await event.SendMessage("Конечно, давайте заполним анкету заново. Постарайтесь ответить на как можно большее количество вопросов и у Вас обязательно всё получится😉",keyboard=KeyBoardEmpty())
                self.SetState(self.QuestingState)
                self._pull = self._reader.getQuestPull()
                
                #вставим в answer list from КОСТЫЛЬ
                my_dict = {"UserID": self.userID}
                self._pull.setAnswer(my_dict)
                self._pull.id-=1
                
                await self.QuestingSend(event)
                return 
        elif event.GetMessage() == "В меню":
                await self.FirstState(event)
                return 
        else:
                event.GetMessage() == "⚠️Такого варианта ответа нет"
                await self.CheckAnswers(event,self._pull.getRawAnswerList())
                return
        return

    async def GetCheckMessage(self,List) -> str:
        message = " "
        for data in self._pull.dictClass.getData():  
                collumb = data["baseCollumb"]
                if  not (List.get(collumb) is None):
                    message +="✍️ "+ data["checktext"] + " :\n ✅" + str(List[collumb])+ "\n---------------------------------------------------\n"
        return message
    
    async def CheckAnswers(self, event:Event,List):
        await event.SendKeyBoardAnswer()
        keyboard = event.KeyBoard()
        keyboard.addButton("Все верно, отправить",color= KeyBoard.ButtonColor.green,buttontype=KeyBoard.ButtonType.text, payload={"type": "Send"})
        keyboard.addButton("Заполнить заново",color= KeyBoard.ButtonColor.blue, buttontype=KeyBoard.ButtonType.text, payload={"type": "Retry"})
        keyboard.addLine()
        keyboard.addButton("В меню",color= KeyBoard.ButtonColor.red, buttontype=KeyBoard.ButtonType.text, payload={"type": "cancel"})
        if await self.ReplyChecker(event):
            return
        message = await self.GetCheckMessage(List)
        await event.SendMessage(message)
        await event.SendMessage("Пожалуйста, подтвердите своё действие: ",keyboard=keyboard)    
        self.SetState(self.FinaleState)
        return 
    


    async def Repair(self, event:Event):
        
        #ставим пул
        self._pull = self._reader.getQuestPull()
        #теперь поочередно нужно заполнить его из БД, для этого нужно базы данных вырывать ответы по типам колонок
        for x in self._reader.getData():
            self.quest = self._pull.giveQuest()
            #вставить колонка из quest/ответ из бд

            #заполним сначала raw 
            if self.quest.getQuestType() is QuestTypes.Date:
                answer = datetime.datetime.fromtimestamp(await self.Base.getField(self.quest.getQuestColumb(),self.userID))
                answer = answer.strftime("%d.%m.%Y")
            else:
                answer =  await self.Base.getField(self.quest.getQuestColumb(),self.userID)
            answer =  {self.quest.getQuestColumb() :answer}
            self._pull.setRawAnswer(answer)
            
            #теперь обычный 
            answer =  await self.Base.getField(self.quest.getQuestColumb(),self.userID)
            answer =  {self.quest.getQuestColumb() :answer}
            self._pull.setAnswer(answer)
        return
