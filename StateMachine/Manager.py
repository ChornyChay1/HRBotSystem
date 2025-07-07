from Core.API import *
from Service.DB import DB
from Service.TG import TG
from Utill.FSM import FSM
from datetime import datetime
from Service.JSONQuestConvert import *
import os
import csv
import io


class Manager(FSM):
    def __init__(self, peer_id:int, s_dict: dict, parent_service: TG) -> None:
        self._peer_id = peer_id

        self._s_dict = s_dict   
        self.Base: DB   = self._s_dict["BD"]
        self._isFirstly = True;
        self._choiceParameterMode = 1;
        self._sortParameterMode = 1;
        self._reader: JSONQuestReader = self._s_dict["reader"]
        self._data = self._reader.getData()
        self._oldMsg = 0
        
        self._attributeMessage = None
        self._attribute = None
        self._tmp = None
        
        self._searchMode = True
        
        self._reportYear = None
        
        self.tg:TG = parent_service
       
        self._sortingBy = "DaysOfWork"
        self._sortingMessage = "Количество дней работы"

        self._actuality = f"QuestingDate>={int((datetime.utcnow() - timedelta(days=7)).timestamp())}"
        self._actualityMessage = "Неделя"

        self._whiteListMessage = ["Статус: Свободный","Возраст: от 16"]
        self._blackListMessage = []        

        self._whiteList = ["Status = 'FREE'","DateOfBirth<=1230067631"]
        self._blackList = []

        super().__init__()
        

          
    async def Save(self) -> dict:
        vars_to_save = [
        "_isFirstly", "_choiceParameterMode", "_sortParameterMode", "_oldMsg",
        "_attributeMessage", "_attribute", "_tmp", "_sortingBy",
        "_sortingMessage", "_actuality", "_actualityMessage",
        "_whiteListMessage", "_blackListMessage", "_whiteList", "_blackList"
        ]
        saved_dict = {var: getattr(self, var) for var in vars_to_save}
        return None
   
    async def Load(self, data:dict):
        return
        for var_name, var_value in data.items():
            setattr(self, var_name, var_value)
        self.SetState(self.FirstState)
        pass
       
    async def OldKeyboardCallBack(self, event: Event):
        if event.GetEventType() is EventType.KeyBoardEvent:
            if event.GetMessageID() < self._oldMsg:
                await event.SendKeyBoardAnswer()
                await self.tg.DeleteMessage(self._peer_id,event.GetMessageID())
                return True
        return False


    async def FirstState(self, event: Event):
        if await self.OldKeyboardCallBack(event):
            return


        if event.GetKeyBoardEvent().get("Type") == "Search":
            self.SetState(self.SearchState)
            await self.SearchState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "Contact":
            self.SetState(self.ContactState)
            await self.ContactState(event)
            return
        await event.SendKeyBoardAnswer()
        keyboard = event.KeyBoard(inline = True)
        keyboard.addButton("Режим поиска", payload={"Type": "Search"})
        keyboard.addButton("Режим взаимодействия", payload={"Type": "Contact"})
        if self._isFirstly:
            self._isFirstly = False

            self._oldMsg= await event.SendMessage("Пожалуйста, выберите режим работы", keyboard=keyboard)
        else:
            await event.EditKeyBoardMessage("Пожалуйста, выберите режим работы", keyboard=keyboard)
        return
    

    async def ContactState(self, event: Event):
        if await self.OldKeyboardCallBack(event):
            return        

        if event.GetKeyBoardEvent().get("Type") == "StatusChange":
            self.SetState(self.StatusChangeState)
            self._attribute = None
            await self.StatusChangeState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "MonthReport":
            self.SetState(self.MonthReportState)
            self._attribute = None
            await self.MonthReportState(event)
            return        


        if event.GetKeyBoardEvent().get("Type") == "BackToFirstState":
            self.SetState(self.FirstState)
            await self.FirstState(event)
            return
        await event.SendKeyBoardAnswer()
        keyboard = event.KeyBoard(inline = True)
        keyboard.addButton("Настроить статус претендента по ID", payload={"Type": "StatusChange"})
        keyboard.addButton("Получить отчёт по месяцам", payload={"Type": "MonthReport"})
        keyboard.addLine()
        keyboard.addButton("⬅️ Назад", payload={"Type": "BackToFirstState"})
        await event.EditKeyBoardMessage("Пожалуйста, выберите режим работы", keyboard=keyboard)
        return
    
    async def StatusChangeState(self, event: Event):
        if await self.OldKeyboardCallBack(event):
            return

        if event.GetEventType() == EventType.NewMessage:
            
            
            if await self.Base.searchField("UserID",event.GetMessage()) != None:
                self._attribute = event.GetMessage()
                # self.Base.upsertData("UserID",event.GetMessage)
                self.SetState(self.StatusChangeVarState)
                await self.StatusChangeVarState(event)
                return
            else:
                await self.tg.DeleteMessage(self._peer_id,self._oldMsg)
                self._oldMsg= event.SendMessage("ID не найдено, проверьте его корректность")
                self._attribute = ""
        if event.GetKeyBoardEvent().get("Type") == "BackToContactState":
            self.SetState(self.ContactState)
            await self.ContactState(event)
            return
        await event.SendKeyBoardAnswer()
        keyboard = event.KeyBoard(inline = True)
        keyboard.addButton("⬅️ Назад", payload={"Type": "BackToContactState"})
        if self._attribute==None:
            self._oldMsg= await event.EditKeyBoardMessage("Пожалуйста, введите ID пользователя. Его вы можете узнать из Excel отчёта.", keyboard=keyboard)
        else: 
            await self.tg.DeleteMessage(self._peer_id,self._oldMsg)
            self._oldMsg= await event.SendMessage("Пожалуйста, введите ID пользователя. Его вы можете узнать из Excel отчёта.", keyboard=keyboard)
        return
    





    

    async def StatusChangeVarState(self, event: Event):
        if await self.OldKeyboardCallBack(event):
            return        

        await event.SendKeyBoardAnswer()
        if event.GetKeyBoardEvent().get("Type") == "BROKE":
            await self.Base.upsertData("UserID",self._attribute,{"Status":"BROKE"})
            self._attribute = None
            self.SetState(self.ContactState)
            await self.ContactState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "WORK":
            await self.Base.upsertData("UserID",self._attribute,{"Status":"WORK"})
            self._attribute = None
            self.SetState(self.ContactState)
            await self.ContactState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "FREE":
            await self.Base.upsertData("UserID",self._attribute,{"Status":"FREE"})
            self._attribute = None
            self.SetState(self.ContactState)
            await self.ContactState(event)
            return
        keyboard = event.KeyBoard(inline = True)
        keyboard.addButton("Свободен", payload={"Type": "FREE"})
        keyboard.addLine()
        keyboard.addButton("Забракован", payload={"Type": "BROKE"})
        keyboard.addLine()
        keyboard.addButton("Работает", payload={"Type": "WORK"})
        keyboard.addLine()
        keyboard.addButton("⬅️ Назад", payload={"Type": "BackParameterChoiceState"})
        currentStatus = await self.Base.getField("Status",self._attribute)
        if currentStatus == "FREE":
                    mess = "Текущий статус: Свободен"     
        if currentStatus == "BROKE":
                    mess = "Текущий статус: Забракован"  
        if currentStatus == "WORK":
                    mess = "Текущий статус: Работает"      
        await self.tg.DeleteMessage(self._peer_id,self._oldMsg)
        self._oldMsg= await event.SendMessage(mess+"\n\nВыберите вариант:", keyboard=keyboard)
    
    #определяются параметры поиска и сам поиск

    async def CheckTask(self):
        mess = ""
        for el in self._whiteListMessage:
           mess += "\n🟢"
           mess+=el
        mess += "\n"
        for el in self._blackListMessage:
           mess += "\n🔴"
           mess+=el
        mess += "\n\n🟡Сортируем по параметру:\t" + str(self._sortingMessage)
        if self._sortParameterMode == 1:
            mess+="⬆️"
        else:
            mess+="⬇️"
        mess += "\n🟣Актуальность:\t" + str(self._actualityMessage)
        return mess
        
    async def SearchState(self, event: Event):
        if await self.OldKeyboardCallBack(event):
            return        

        await event.SendKeyBoardAnswer()
        if event.GetKeyBoardEvent().get("Type") == "BackFirstState":
            self.SetState(self.FirstState)
            await self.FirstState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "SearchParameter":
            self.SetState(self.ParameterChoiceState)
            await self.ParameterChoiceState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "SortingParameter":
            self.SetState(self.SortModeState)
            await self.SortModeState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "Actuality":
            self.SetState(self.ActualityState)
            await self.ActualityState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "MakeSearch":
            self._searchMode = event.GetKeyBoardEvent().get("Mode")
            self.SetState(self.MakeChoiceState)
            await self.MakeChoiceState(event)
            return
        mess = await self.CheckTask()
        keyboard = event.KeyBoard(inline = True)
        keyboard.addButton("Настроить параметры выборки", payload={"Type": "SearchParameter"})
        keyboard.addButton("Настроить параметр сортировки", payload={"Type": "SortingParameter"})
        keyboard.addButton("Настроить актуальность выборки", payload={"Type": "Actuality"})
        keyboard.addLine()
        keyboard.addButton("Краткий отчёт🔍", payload={"Type": "MakeSearch","Mode":False})
        keyboard.addButton("Полный отчёт🔍", payload={"Type": "MakeSearch","Mode":True})

        keyboard.addLine()
        keyboard.addButton("⬅️ Назад", payload={"Type": "BackFirstState"})
        if self._attribute != None:
            await self.tg.DeleteMessage(self._peer_id,self._oldMsg)
            self._oldMsg= await event.SendMessage(mess + "\n\nВыберите действие:", keyboard=keyboard)
            self._attribute = None
            return
        else:
            await event.EditKeyBoardMessage(mess + "\n\nВыберите действие:", keyboard=keyboard)
            return
        # self.SetState(self.ManagerAnswerState)
        return
        

    async def ActualityState(self, event: Event):
        if await self.OldKeyboardCallBack(event):
            return        

        await event.SendKeyBoardAnswer()
        if event.GetKeyBoardEvent().get("Type") == "BackSearchState":
            self._attribute = None
            self._attributeMessage = None
            self.SetState(self.SearchState)
            await self.SearchState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "Week":
            self._actuality = f"QuestingDate>={int((datetime.utcnow() - timedelta(days=7)).timestamp())}"
            self._actualityMessage = "Неделя"
            self.SetState(self.SearchState)
            await self.SearchState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "Month":
            self._actuality = f"QuestingDate>={int((datetime.utcnow() - timedelta(days=365/12)).timestamp())}"
            self._actualityMessage = "Месяц"
            self.SetState(self.SearchState)
            await self.SearchState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "Year":
            self._actuality = f"QuestingDate>={int((datetime.utcnow() - timedelta(days=365)).timestamp())}"
            self._actualityMessage = "Год"
            self.SetState(self.SearchState)
            await self.SearchState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "AllTime":
            self._actuality = f"QuestingDate>=0"
            self._actualityMessage = "Всё время"
            self.SetState(self.SearchState)
            await self.SearchState(event)
            return
        keyboard = event.KeyBoard(inline = True)
        keyboard.addButton("Неделя", payload={"Type": "Week"})
        keyboard.addButton("Месяц", payload={"Type": "Month"})
        keyboard.addButton("Год", payload={"Type": "Year"})
        keyboard.addButton("Всё время", payload={"Type": "AllTime"})
        keyboard.addLine()
        keyboard.addButton("⬅️ Назад", payload={"Type": "BackSearchState"})
        await event.EditKeyBoardMessage("Выберите режим настройки параметра:", keyboard=keyboard)
        
    #опеределяется, в какой список мы добавляем значения чёрный или белый
    async def ChoiceModeState(self, event: Event):
        if await self.OldKeyboardCallBack(event):
            return

        await event.SendKeyBoardAnswer()
        if event.GetKeyBoardEvent().get("Type") == "BackParameterChoiceState":
            
            self.SetState(self.ParameterChoiceState)
            self._attribute = None
            self._attributeMessage = None
            await self.ParameterChoiceState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "Negative":
            self._choiceParameterMode = -1
            self.SetState(self._tmp)
            await self._tmp(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "Positive":
            self._choiceParameterMode = 1
            self.SetState(self._tmp)
            await self._tmp(event)
            return
        keyboard = event.KeyBoard(inline = True)
        keyboard.addButton("Установить параметр", payload={"Type": "Positive"})
        keyboard.addButton("Не допускать", payload={"Type": "Negative"})
        keyboard.addLine()
        keyboard.addButton("⬅️ Назад", payload={"Type": "BackParameterChoiceState"})
        await event.EditKeyBoardMessage("Выберите режим настройки параметра:", keyboard=keyboard)
        
  
         
    async def ParameterChoiceState(self, event: Event):
        if await self.OldKeyboardCallBack(event):
            return        

        await event.SendKeyBoardAnswer()
        if event.GetKeyBoardEvent().get("Type") == "Sex":
            self._attribute = "Sex"
            self._attributeMessage = "Пол"
            self._choiceParameterMode = 1;
            self.SetState(self.VarChoice)
            await self.VarChoice(event)
            # await self.VarChoice(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "Work":
            self._attribute = "Position"
            self._attributeMessage = "Желаемая позиция"
            self.SetState(self.ChoiceModeState)
            self._tmp = self.VarChoice
            await self.ChoiceModeState(event)
            # await self.VarChoice(event)
            return
        
        if event.GetKeyBoardEvent().get("Type") == "Age":
            self._attribute = "DateOfBirth"
            self._attributeMessage = "Возраст"
            self._choiceParameterMode = 1;
            self.SetState(self.AgeChoice)
            await self.AgeChoice(event)
            # await self.IntChoice(event)
            return
        
        if event.GetKeyBoardEvent().get("Type") == "Period":
            self._attribute = ""
            self._choiceParameterMode = 1;
            self.SetState(self.DataChoice)
            await self.DataChoice(event)
            # await self.DataChoice(event)
            return
        
        if event.GetKeyBoardEvent().get("Type") == "BackSearchState":
            self.SetState(self.SearchState)
            await self.SearchState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "Other":
            self.SetState(self.OtherChoiceState)
            await self.OtherChoiceState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "ParameterResetMenu":
            self.SetState(self.ParameterResetMenuState)
            await self.ParameterResetMenuState(event)
            return
        mess = await self.CheckTask()
        keyboard = event.KeyBoard(inline = True)
        keyboard.addButton("Возраст", payload={"Type": "Age"})
        keyboard.addButton("Пол ", payload={"Type": "Sex"})
        keyboard.addButton("Период работы ", payload={"Type": "Period"})
        keyboard.addButton("Cпециализация", payload={"Type": "Work"})
        keyboard.addLine()
        keyboard.addButton("Другое ", payload={"Type": "Other"})
        keyboard.addLine()
        keyboard.addButton("Меню сброса параметров ❌", payload={"Type": "ParameterResetMenu"})
        keyboard.addLine()
        keyboard.addButton("⬅️ Назад ", payload={"Type": "BackSearchState"})
        if self._attribute != None:
            await self.tg.DeleteMessage(self._peer_id,self._oldMsg)
            self._oldMsg= await event.SendMessage(mess + "\n\nВыберите параметр, с которым будем работать:", keyboard=keyboard)
            self._attribute = None
            return
        else:
            await event.EditKeyBoardMessage(mess + "\n\nВыберите параметр, с которым будем работать:", keyboard=keyboard)
            return
        
         
    async def ParseData(self,message):
        pattern = r'(от|до)\s*(\d{2}\.\d{2}\.\d{4})\s*(до)?\s*(\d{2}\.\d{2}\.\d{4})?'
        match = re.search(pattern, message)

        if match:
            direction_start = match.group(1) if match.group(1) else "от"
            direction_end = match.group(3) if match.group(3) else "до"
            
            range_start = datetime.strptime(match.group(2), '%d.%m.%Y').timestamp() if match.group(2) else None
            range_end = datetime.strptime(match.group(4), '%d.%m.%Y').timestamp() if match.group(4) else None

            return direction_start, range_start, direction_end, range_end
        else:
            return None
         
    async def ParseInt(self, message):
        pattern = r'(от|до)\s*(\d+)\s*(до)?\s*(\d+)?'
        match = re.search(pattern, message)

        if match:
            direction_start = match.group(1) if match.group(1) else "от"
            direction_end = match.group(3) if match.group(3) else "до"

            range_start = int(match.group(2)) if match.group(2) else None
            range_end = int(match.group(4)) if match.group(4) else None


            return direction_start, range_start, direction_end, range_end
        else:
            return None
        
    async def AgeToUnix(self, age):
        try: 
            age_years = int(age)
            age_seconds = int(age_years*365.25*24*60*60) 
            current_date = int(time.time())
            birthday = current_date - age_seconds
           
            return birthday
        except ValueError:
            return "Ошибка: Некорректный формат возраста"
        
    async def DateToAgeUnix(self, date):
        try:
            birthday = date
            current_date = int(time.time())
            age_seconds = current_date - birthday
            age = int(age_seconds/365.25/24/60/60)
            return age
        except ValueError:
            return "Ошибка: Некорректный формат возраста"
        

    async def UnixToDate(self,timestamp_str):
        try: 
            timestamp = float(timestamp_str)
         
            if timestamp < 0:
                dt_object = datetime(1970, 1, 1) + timedelta(seconds=timestamp)
            else:
                dt_object = datetime.utcfromtimestamp(timestamp)
           
        
            # Форматируем дату в требуемый формат
            formatted_date = dt_object.strftime('%d.%m.%Y')
        
            return formatted_date
        except ValueError:
            return "Ошибка: Некорректный формат Unix timestamp"
         
    async def CheckCondition(self, list):
        condition_found = False
        j=-1
        for i in range(len(list)):
            if self._attribute in list[i]:
                condition_found = True
                j = i
                break
        return condition_found,j
    
    async def InsertIn(self,mess,messCheck):     
        res1 = await self.CheckCondition(self._whiteList)
        res2 = await self.CheckCondition(self._blackList)
        
        if res1[0]:
            self._whiteList.pop(res1[1])
            self._whiteListMessage.pop(res1[1])
        if res2[0]:
            self._blackList.pop(res1[1])
            self._blackListMessage.pop(res1[1])
        if self._attribute == "DateOfStart":
            self._attribute = "DateOfFinish"
            self._attributeMessage = "Дата завершения работы"
            res1 = await self.CheckCondition(self._whiteList)
            res2 = await self.CheckCondition(self._blackList)
            if res1[0]:
                self._whiteList.pop(res1[1])
                self._whiteListMessage.pop(res1[1])
            if res2[0]:
                self._blackList.pop(res1[1])
                self._blackListMessage.pop(res1[1])
                    
        if self._choiceParameterMode==1:
         self._whiteList.append(mess)
         self._whiteListMessage.append(messCheck)
        else:
         self._blackList.append(mess)
         self._blackListMessage.append(messCheck)

        


    async def AgeChoice(self, event: Event):  
        if await self.OldKeyboardCallBack(event):
            return

        if event.GetEventType() is EventType.NewMessage:
            mess = str(self._attribute)
            messCheck = str(self._attributeMessage)
            
            if await self.ParseInt(event.GetMessage())!= None:
                 result = await self.ParseInt(event.GetMessage())
                 if result[0] == "от":
                    mess += "<="
                    messCheck += " от "
                 elif result[0] == " до ":
                    mess += ">="
                    messCheck += " до "
                 if result[1]:
                     mess+=str(await self.AgeToUnix( result[1]))
                     messCheck+=str(str(result[1]))
                 if result[2] and result[3] and result[0]=="от":
                     mess+=(" AND "+str(self._attribute)+">="  + str(await self.AgeToUnix((result[3]))))
                     messCheck+=(" до "  + str(result[3]))
                 
                 await self.InsertIn(mess,messCheck)

                    
            self.SetState(self.ParameterChoiceState)
            await self.ParameterChoiceState(event)
            return
        elif event.GetKeyBoardEvent().get("Type") == "BackParameterChoiceState":
            self._attribute = None
            self._attributeMessage = None
            self.SetState(self.ParameterChoiceState)
            await self.ParameterChoiceState(event)
            return  
        else:
            await event.SendKeyBoardAnswer()
            keyboard = event.KeyBoard(inline = True)
            keyboard.addButton("⬅️ Назад ", payload={"Type": "BackParameterChoiceState"})
            await event.EditKeyBoardMessage("Введите значение в формате 'от' *число* 'до' *число*", keyboard=keyboard)



    async def IntChoice(self, event: Event):  
        if await self.OldKeyboardCallBack(event):
            return        

        if event.GetEventType() is EventType.NewMessage:
            mess = str(self._attribute)+" :"
            messCheck = str(self._attributeMessage)
            
            if await self.ParseInt(event.GetMessage())!= None:
                 result = await self.ParseInt(event.GetMessage())
                 if result[0] == "от":
                    mess +=">="
                    messCheck+=" от "
                 elif result[0] == " до ":
                    mess += "<="
                    messCheck+=" до "
                 if result[1]:
                     mess+=str(result[1])
                     messCheck+=str(str(result[1]))
                 if result[2] and result[3] and result[0]=="от":
                     mess+=(" AND "+str(self._attribute)+"<="  + str(result[3]))
                     messCheck+=(" до "  + str(result[3]))
                 
                 await self.InsertIn(mess,messCheck)

                    
            self.SetState(self.ParameterChoiceState)
            await self.ParameterChoiceState(event)
            return
        elif event.GetKeyBoardEvent().get("Type") == "BackParameterChoiceState":
            self._attribute = None
            self._attributeMessage = None
            self.SetState(self.ParameterChoiceState)
            await self.ParameterChoiceState(event)
            return  
        else:
            await event.SendKeyBoardAnswer()
            keyboard = event.KeyBoard(inline = True)
            keyboard.addButton("⬅️ Назад ", payload={"Type": "BackParameterChoiceState"})
            await event.EditKeyBoardMessage("Введите значение в формате 'от' *число* 'до' *число*", keyboard=keyboard)
            
    async def DataChoice(self, event: Event):  
        if await self.OldKeyboardCallBack(event):
            return    
    
        if event.GetEventType() is EventType.NewMessage:
            mess = "DateOfStart"
            messCheck = "Дата начала работы :"
            if await self.ParseData(event.GetMessage())!= None:
                 result = await self.ParseData(event.GetMessage())
                 if result[0] == "от":
                    mess +=">="
                    messCheck +=" от "
                 elif result[0] == "до":
                    mess = "DateOfFinish"
                    messCheck ="Дата окончания работы :"
                    mess += "<="
                    messCheck +=" до "

                 if result[1]:
                     mess+=str(result[1])
                     messCheck += str(await self.UnixToDate((result[1])))
                 if result[2]=="до" and result[3] and result[0]=="от":
                     mess+=(" AND "+"DateOfFinish"+"<="  + str(result[3]))
                     messCheck +=("\n Дата окончания работы: до "  + str(await self.UnixToDate((result[3]))))
            
            self._attribute = "DateOfStart"
            self._attributeMessage = "Дата начала работы"
            await self.InsertIn(mess,messCheck)
            
            self.SetState(self.ParameterChoiceState)
            await self.ParameterChoiceState(event)
            return
        elif event.GetKeyBoardEvent().get("Type") == "BackParameterChoiceState":
            self._attribute = None
            self._attributeMessage = None
            self.SetState(self.ParameterChoiceState)
            await self.ParameterChoiceState(event)
            return  
        else:
            await event.SendKeyBoardAnswer()
            keyboard = event.KeyBoard(inline = True)
            keyboard.addButton("⬅️ Назад ", payload={"Type": "BackParameterChoiceState"})
            await event.EditKeyBoardMessage("Введите значение в формате 'от' *число* 'до' *число*", keyboard=keyboard)
            

    async def VarChoice(self, event: Event):  
        if await self.OldKeyboardCallBack(event):
            return        

        await event.SendKeyBoardAnswer()
        if event.GetKeyBoardEvent().get("Type") == "var":
            for x in self._data:
                if x.get("baseCollumb")==self._attribute:
                    quest = x
                    break
                    
            mess=self._attribute + "="+"'"+quest.get("variant")[event.GetKeyBoardEvent().get("SType")-1]+"'"
            messCheck=self._attributeMessage + ": " +quest.get("variant")[event.GetKeyBoardEvent().get("SType")-1]

            await self.InsertIn(mess,messCheck)
            self._attribute = None
            self._attributeMessage = None
            
            self.SetState(self.ParameterChoiceState)
            await self.ParameterChoiceState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "BackParameterChoiceState":
            self._attribute = None
            self._attributeMessage = None
            self.SetState(self.ParameterChoiceState)
            await self.ParameterChoiceState(event)
            return
        keyboard = event.KeyBoard(inline = True)
        for quest in self._data:
            if quest.get("baseCollumb")==self._attribute:
                i=0
                for x in quest.get("variant"):
                    i+=1
                    self._tmp = str(x)
                    keyboard.addButton(x, payload={"Type": "var","SType": i})
                    if i%2==0 and i<=len(self._data):
                        keyboard.addLine()
                break
        if i!=0:
            keyboard.addLine()
        keyboard.addButton("⬅️ Назад", payload={"Type": "BackParameterChoiceState"})
                    
        await event.EditKeyBoardMessage("Выберите вариант:", keyboard=keyboard)
        
    async def StatusChoiceState(self, event: Event):  
        if await self.OldKeyboardCallBack(event):
            return        

        await event.SendKeyBoardAnswer()
        if event.GetKeyBoardEvent().get("Type") == "BROKE":
            self._attribute = "Status"
            self._attributeMessage = "Статус"
            await self.InsertIn("Status = 'BROKE'","Статус: Забракован")
            self._attribute = None
            self._attributeMessage = None
            self.SetState(self.ParameterChoiceState)
            await self.ParameterChoiceState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "WORK":
            self._attribute = "Status"
            self._attributeMessage = "Статус"
            await self.InsertIn("Status = 'WORK'","Статус: Работает")
            self._attribute = None
            self._attributeMessage = None
            self.SetState(self.ParameterChoiceState)
            await self.ParameterChoiceState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "FREE":
            self._attribute = "Status"
            self._attributeMessage = "Статус"
            await self.InsertIn("Status = 'FREE'","Статус: Свободный")
            self._attribute = None
            self._attributeMessage = None
            self.SetState(self.ParameterChoiceState)
            await self.ParameterChoiceState(event)
            return
        keyboard = event.KeyBoard(inline = True)
        keyboard.addButton("Свободен", payload={"Type": "FREE"})
        keyboard.addLine()
        keyboard.addButton("Забракован", payload={"Type": "BROKE"})
        keyboard.addLine()
        keyboard.addButton("Работает", payload={"Type": "WORK"})
        keyboard.addLine()
        keyboard.addButton("⬅️ Назад", payload={"Type": "BackParameterChoiceState"})
                    
        await event.EditKeyBoardMessage("Выберите вариант:", keyboard=keyboard)
            

    async def MonthReportState(self, event: Event):
        if event.GetEventType() == EventType.NewMessage:
            
            try:
                parsed_year = int(event.GetMessage())
                current_year = datetime.now().year
                if current_year <= parsed_year:
                    self._reportYear = parsed_year
                    # self.Base.upsertData("UserID", event.GetMessage)
                    self.SetState(self.WritingMonthReportState)
                    await self.WritingMonthReportState(event)
                    return
                else:
                    await self.tg.DeleteMessage(self._peer_id,self._oldMsg)
                    self._attribute = ""
            except ValueError:
                    await self.tg.DeleteMessage(self._peer_id,self._oldMsg)
                    self._attribute = ""
        if event.GetKeyBoardEvent().get("Type") == "BackToContactState":
            self.SetState(self.ContactState)
            await self.ContactState(event)
            return
        await event.SendKeyBoardAnswer()
        keyboard = event.KeyBoard(inline = True)
        keyboard.addButton("⬅️ Назад", payload={"Type": "BackToContactState"})
        if self._attribute==None:
            self._oldMsg= await event.EditKeyBoardMessage("Пожалуйста, введите год за которых Вы бы хотели получить отчёт", keyboard=keyboard)
        else: 
            await self.tg.DeleteMessage(self._peer_id,self._oldMsg)
            self._oldMsg= await event.SendMessage("Пожалуйста, введите год за которых Вы бы хотели получить отчёт", keyboard=keyboard)
        return
    



    async def WritingMonthReportState(self, event: Event):
        await event.SendKeyBoardAnswer()
        if event.GetKeyBoardEvent().get("Type") == "BackToContactState":
            self.SetState(self.ContactState)
            await self.ContactState(event)
            return

        await self.tg.DeleteMessage(self._peer_id,self._oldMsg)
        export_msg_id = await event.SendMessage(f"Экспорт данных. Пожалуйста подождите....")
        
        
        res = await self.Base.makeMonthReport(self._reportYear)

        # Используем переменную output_string вместо создания файла
        output_string = ""

        try:
                output_buffer = io.StringIO()
                csv_writer = csv.DictWriter(output_buffer, fieldnames=res.keys(), delimiter='\t')

                current_date_time = datetime.now()
                output_buffer.write(f"Отчёт от {current_date_time.strftime('%d-%m-%Y   %H:%M')} Количество человек на {self._reportYear} год\n\n")

                # Записываем заголовки
                csv_writer.writeheader()
                 
                csv_writer.writerow(res)
                output_string = output_buffer.getvalue()
                file_stream = io.BytesIO(output_string.encode('utf-16'))

                # Отправляем сообщение с результатами
                await event.SendFile(file_stream, f"Годовой отчёт за {self._reportYear} год от {current_date_time.strftime('%d-%m-%Y   %H-%M')} .csv\n\n")


        except Exception as e:
            await event.SendMessage(f"Запрос ничего не выдал ")

        finally:
            keyboard = event.KeyBoard(inline=True)
            keyboard.addButton("Вернуться к работе", payload={"Type": "BackToContactState"})
            await self.tg.DeleteMessage(self._peer_id, export_msg_id)
            self._oldMsg= await event.SendMessage(f"Поиск завершен✅", keyboard=keyboard)
      
        


    #если добавили "другое"
    async def OtherChoiceState(self, event: Event):
        if await self.OldKeyboardCallBack(event):
            return        


        await event.SendKeyBoardAnswer()
        if event.GetKeyBoardEvent().get("T") == "O":
            for quest in self._data:
                if quest.get("baseCollumb") == event.GetKeyBoardEvent().get("N"):
                    current_quest = quest
                    break
            if current_quest.get("type") == "text" or current_quest.get("type") == "social"or current_quest.get("type") == "email":
                self._choiceParameterMode = 1
                self._attribute = current_quest.get("baseCollumb")
                self._attributeMessage = current_quest.get("checktext")
                mess = current_quest.get("baseCollumb") + " IS NOT NULL"
                messCheck = current_quest.get("checktext") + ": поле заполнено"
                await self.InsertIn(mess,messCheck)
                self._attribute = None
                self._attributeMessage = None
                self.SetState(self.ParameterChoiceState)
                await self.ParameterChoiceState(event)
                return
            elif current_quest.get("type") == "int":
                self._attribute = event.GetKeyBoardEvent().get("N")
                for quest in self._data:
                    if quest.get("baseCollumb") == event.GetKeyBoardEvent().get("N"):
                        self._attributeMessage = quest.get("checktext")
                        break
                self.SetState(self.IntChoice)
                await self.IntChoice(event) 
                return
            elif current_quest.get("type") == "choice":
                self._attribute = event.GetKeyBoardEvent().get("N")
                for quest in self._data:
                    if quest.get("baseCollumb") == event.GetKeyBoardEvent().get("N"):
                        self._attributeMessage = quest.get("checktext")
                        break
                self.SetState(self.ChoiceModeState)
                self._tmp = self.VarChoice
                await self.ChoiceModeState(event)
                # await self.VarChoice(event)
                return
        if event.GetKeyBoardEvent().get("Type") == "Status":
            self.SetState(self.StatusChoiceState)
            await self.StatusChoiceState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "BackParameterChoiceState":
            self._attribute = None
            self._attributeMessage = None
            self.SetState(self.ParameterChoiceState)
            await self.ParameterChoiceState(event)
            return
       
        keyboard = event.KeyBoard(inline = True)
        i = 0
        for quest in self._data:
            if quest.get("inOther"):
                i+=1
                keyboard.addButton(quest.get("checktext"), payload={"T": "O","N": quest.get("baseCollumb")})
                if i%2==0 and i<=len(self._data):
                    keyboard.addLine()
        if i!=0:
            keyboard.addLine()
        keyboard.addButton("Статус ", payload={"Type": "Status"})
        keyboard.addLine()
        keyboard.addButton("⬅️ Назад", payload={"Type": "BackParameterChoiceState"})
        await event.EditKeyBoardMessage("Выберите параметр, с которым будем работать:", keyboard=keyboard)
        
 #меню сброса параметров     
    async def ParameterResetMenuState(self, event: Event):
        if await self.OldKeyboardCallBack(event):
            return        

        await event.SendKeyBoardAnswer()
        if event.GetEventType() == EventType.NewMessage:
            user_input = event.GetMessage()
            processed_input = self.process_user_input(user_input)

            if processed_input is None: 
                await self.tg.DeleteMessage(self._peer_id,self._oldMsg)

                self._oldMsg= await event.SendMessage("Некорректный ввод. Пожалуйста, введите правильные номера параметров через запятую.")
                return
             
            self.remove_elements_by_ids(processed_input)
            self._attribute = ""
            self.SetState(self.ParameterChoiceState)
            await self.ParameterChoiceState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "BackParameterChoiceState":
            self.SetState(self.ParameterChoiceState)
            await self.ParameterChoiceState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "ResetAll":
            self._whiteListMessage = ["Статус: Свободный","Возраст: от 16"]
            self._blackListMessage = []        
            self._whiteList = ["Status = 'FREE'","DateOfBirth>=1230067631"]
            self._blackList = []
            self.SetState(self.ParameterChoiceState)
            await self.ParameterChoiceState(event)
            return
        i = 1
        mess = ""
        for el in self._whiteListMessage:
           mess += f"\n{i}\t🟢"
           mess+=el
           i+=1
        for el in self._blackListMessage:
           mess += f"\n{i}\t🔴"
           mess+=el
           i+=1
        keyboard = event.KeyBoard(inline = True)
        keyboard.addButton("Сбросить всё", payload={"Type": "ResetAll"})
        keyboard.addLine()
        keyboard.addButton("⬅️ Назад", payload={"Type": "BackParameterChoiceState"})
        await event.EditKeyBoardMessage(mess +"\n\nЧерез запятую введите номер параметра выборки который Вы хотите удалить:", keyboard=keyboard)
        
    def process_user_input(self, input_str): 
        if not input_str.replace(',', '').isdigit():
            return None  # Возвращаем None в случае некорректного ввода
         
        input_list = list(set(map(int, input_str.split(','))))

        return input_list

    # Функция удаления элементов из массивов whiteList и blackList
    def remove_elements_by_ids(self, input_ids): 
        for idx in sorted(input_ids, reverse=True):
            if 1 <= idx <= len(self._whiteListMessage):
                self._whiteListMessage.pop(idx - 1)
                self._whiteList.pop(idx - 1)
            elif len(self._whiteListMessage) < idx <= len(self._whiteListMessage) + len(self._blackListMessage):
                self._blackListMessage.pop(idx - len(self._whiteListMessage) - 1)
                self._blackList.pop(idx - len(self._whiteListMessage) - 1)

        
    #ЗДЕСЬ СОСТОЯНИЯ ДЛЯ ВЫБОРА СОРТИРОВКИ


    #обратная или прямая сортировка        
    async def SortModeState(self, event: Event):
        if await self.OldKeyboardCallBack(event):
            return        

        await event.SendKeyBoardAnswer()
        if event.GetKeyBoardEvent().get("Type") == "BackSearchState":
            self.SetState(self.SearchState)
            await self.SearchState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "Negative":
            self._sortParameterMode = -1
            self.SetState(self.ParameterSortState)
            await self.ParameterSortState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "Positive":
            self._sortParameterMode = 1
            self.SetState(self.ParameterSortState)
            await self.ParameterSortState(event)
            return
        keyboard = event.KeyBoard(inline = True)
        keyboard.addButton("От меньшего к большему", payload={"Type": "Positive"})
        keyboard.addButton("От большего к меньшему", payload={"Type": "Negative"})
        keyboard.addLine()
        keyboard.addButton("⬅️ Назад", payload={"Type": "BackSearchState"})
        await event.EditKeyBoardMessage("Выберите режим настройки параметра:", keyboard=keyboard)
         
    async def ParameterSortState(self, event: Event):
        if await self.OldKeyboardCallBack(event):
            return        

        await event.SendKeyBoardAnswer()
        if event.GetKeyBoardEvent().get("Type") == "BackSearchState":
            self.SetState(self.SearchState)
            await self.SearchState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "Other":
            self.SetState(self.OtherSortState)
            await self.OtherSortState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "Age":
            self._sortingBy = "DateOfBirth"   
            self._sortParameterMode*=-1
            self._sortingMessage = "Возраст"
            self.SetState(self.SearchState)
            await self.SearchState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "Days":
            self._sortingBy = "DaysOfWork"   
            self._sortingMessage = "Количество дней работы"
            self.SetState(self.SearchState)
            await self.SearchState(event)
            return
        if event.GetKeyBoardEvent().get("Type") == "QuestingDate":
            self._sortingBy = "QuestingDate"   
            self._sortingMessage = "Дата заполнения анкеты"
            self.SetState(self.SearchState)
            await self.SearchState(event)
            return
        keyboard = event.KeyBoard(inline = True)
        keyboard.addButton("Возраст", payload={"Type": "Age"})
        keyboard.addLine()
        keyboard.addButton("Количество дней работы", payload={"Type": "Days"})
        keyboard.addLine()
        keyboard.addButton("Дата заполнения анкеты", payload={"Type": "QuestingDate"})
        keyboard.addLine()
        keyboard.addButton("Другое ", payload={"Type": "Other"})
        keyboard.addLine()
        keyboard.addButton("⬅️ Назад ", payload={"Type": "BackSearchState"})
        await event.EditKeyBoardMessage("Выберите параметр, с которым будем работать:", keyboard=keyboard)
        
         
    async def OtherSortState(self, event: Event):
        if await self.OldKeyboardCallBack(event):
            return        

        await event.SendKeyBoardAnswer()
        
        if event.GetKeyBoardEvent().get("Type") == "otherChoice":
            self._sortingBy = event.GetKeyBoardEvent().get("SType")
            for quest in self._data:
                if quest.get("baseCollumb")==  self._sortingBy:     
                     self._sortingMessage = quest.get("checktext")
                     break
            self.SetState(self.SearchState)
            await self.SearchState(event)
            return
        
        if event.GetKeyBoardEvent().get("Type") == "BackParameterChoiceState":
            self._attribute = None
            self._attributeMessage = None
            self.SetState(self.ParameterSortState)
            await self.ParameterSortState(event)
            return
       
        keyboard = event.KeyBoard(inline = True)
        i = 0
        for quest in self._data:
            if quest.get("inOther") and quest.get("type") == "int":
                i+=1
                keyboard.addButton(quest.get("checktext"), payload={"Type": "otherChoice","SType": quest.get("baseCollumb")})
                if i%2==0 and i<=len(self._data):
                    keyboard.addLine()
        if i!=0:
            keyboard.addLine()
        keyboard.addButton("⬅️ Назад", payload={"Type": "BackParameterChoiceState"})
        await event.EditKeyBoardMessage("Выберите параметр, с которым будем работать:", keyboard=keyboard)





    async def MakeChoiceState(self, event: Event):
        if await self.OldKeyboardCallBack(event):
            return        

        await event.SendKeyBoardAnswer()
        if event.GetKeyBoardEvent().get("Type") == "BackToSearchState":
            self._attribute = ""
            self.SetState(self.SearchState)
            await self.SearchState(event)
            return


        await self.tg.DeleteMessage(self._peer_id,self._oldMsg)
        export_msg_id = await event.SendMessage(f"Экспорт данных. Пожалуйста подождите....")
        
        
        res = await self.Base.selectData(self._whiteList, self._blackList, self._actuality, self._sortingBy, self._sortParameterMode,self._searchMode)

            
        res = await self.RepairSearchDict(res)
         
        output_string = ""

        try:
            if res is not None:
                output_buffer = io.StringIO()
                csv_writer = csv.DictWriter(output_buffer, fieldnames=res[0].keys(), delimiter='\t')

                current_date_time = datetime.utcnow()
                output_string += f"Отчёт от {current_date_time.strftime('%d-%m-%Y   %H:%M')}\n\n"

                # Записываем заголовки
                csv_writer.writeheader()
                output_string += output_buffer.getvalue()
                output_string += "\n"
                
                output_buffer = io.StringIO()
                csv_writer = csv.DictWriter(output_buffer, fieldnames=res[0].keys(), delimiter='\t')


                # Записываем данные
                csv_writer.writerows(res)
                output_string += output_buffer.getvalue()
                file_stream = io.BytesIO(output_string.encode('utf-16'))
                 
                await event.SendFile(file_stream,f"Отчёт от {current_date_time.strftime('%d-%m-%Y   %H-%M')}.csv\n\n") 
            else:
                self._oldMsg= await event.SendMessage(f"Запрос ничего не выдал")

        except Exception as e:
            await event.SendMessage(f"Запрос ничего не выдал ")

        finally:
            keyboard = event.KeyBoard(inline=True)
            keyboard.addButton("Вернуться к работе", payload={"Type": "BackToSearchState"})
            await self.tg.DeleteMessage(self._peer_id, export_msg_id)
            self._oldMsg= await event.SendMessage(f"Поиск завершен✅", keyboard=keyboard)

    async def RepairSearchDict(self, dictList):
        updated_dict_list = []

        for record in dictList:
            updated_record = record.copy()

            for data_record in self._data:
                base_collumb_value = data_record.get("baseCollumb")
                if base_collumb_value in updated_record: 
                    updated_record[data_record.get("checktext")] = record[data_record.get("baseCollumb")]
                    del updated_record[base_collumb_value]
            updated_record["Возраст"] = await self.DateToAgeUnix(record["DateOfBirth"])
            if "Status" in updated_record:
                if record["Status"] == "FREE":
                    status = "Свободен"
                if record["Status"] == "BROKE":
                    status = "Забракован"
                if record["Status"] == "WORK":
                    status = "Работает"
                updated_record["Статус"] = status
                del updated_record["Status"]
            if "Могу начать работать с" in updated_record:
                date = await self.UnixToDate(updated_record["Могу начать работать с"])
                updated_record["Могу начать работать с"] = date
            if "Хочу закончить работать " in updated_record:
                date = await self.UnixToDate(updated_record["Хочу закончить работать "])
                updated_record["Хочу закончить работать "] = date
            if "DaysOfWork" in updated_record:
                days = int(updated_record["DaysOfWork"])/86400
                updated_record["Дней работает"] = days
                del updated_record["DaysOfWork"]
            if "QuestingDate" in updated_record:
                date = await self.UnixToDate(updated_record["QuestingDate"])
                updated_record["Дата анкетирования"] = date
                del updated_record["QuestingDate"]
            if "Дата рождения" in updated_record:
                date = await self.UnixToDate(updated_record["Дата рождения"])
                updated_record["Дата рождения"] = date

            updated_dict_list.append(updated_record)
            

        return updated_dict_list
        