
import json
import time
import re
from enum import Enum,auto
from datetime import datetime, timedelta
from Core.Service import Service

class QuestTypes(Enum):
    Choice = auto()
    Int = auto()
    Text = auto() 
    CloseText = auto()
    Date = auto()
    Social = auto()
    Phone = auto()
    Email = auto()
    Unknow = auto()
    

class JSONReaderExeptionGlobal(Exception):
    pass
class JSONReaderExeption:
    class FileNotFound(JSONReaderExeptionGlobal):
        pass
    class DataNotSet(JSONReaderExeptionGlobal):
        pass
    class JSONisEmpty(JSONReaderExeptionGlobal):
        pass
    class NoConvertInInt(JSONReaderExeptionGlobal):
        pass 
    class ErrorFormat(JSONReaderExeptionGlobal):
        pass 
    class NoVariantes(JSONReaderExeptionGlobal):
        pass 
    class NotCorrectJSONFile(JSONReaderExeptionGlobal):
        pass 
    
#вопрос, создаётся в questPull
class quest:
    def __init__(self,pull):
        self.__pull = pull
        
        self.__questObj = self.__pull.getActualQuest()
        
        self.__questText = self.__questObj["text"]
        tmp  = self.__questObj.get("type","unknown")
        if tmp == "text":
            self.__questType = QuestTypes.Text
        elif tmp == "date":
            self.__questType = QuestTypes.Date
        elif tmp == "phone":
            self.__questType = QuestTypes.Phone
        elif tmp == "social":
            self.__questType = QuestTypes.Social
        elif tmp == "email":
            self.__questType = QuestTypes.Email
        elif tmp == "int":
            self.__questType = QuestTypes.Int
        elif tmp == "choice":
            self.__questType = QuestTypes.Choice
        elif tmp == "close_text":
            self.__questType = QuestTypes.CloseText
        else: 
            self.__questType = QuestTypes.Unknow
            
        if self.__questType is QuestTypes.Choice:
            self.__questVar = self.__questObj["variant"]
        else:
            self.__questVar = None
        if self.__questType is QuestTypes.CloseText:
            self.__questFormat = self.__questObj["format"]
        else:
            self.__questFormat = None
        self.questCanBeSkiped = self.__questObj.get("canBeSkiped", False)
        self.__questCheck = self.__questObj.get("check")
        self.__questColumb = self.__questObj.get("baseCollumb")
        self.__questIsFinish = False
        

    #геттеры
    def getQuestVar(self):
        return self.__questVar
    def getQuestType(self) -> str:
        return self.__questType
    def getTextQuest(self) -> str:
        return self.__questText
    def getQuestFormat(self) -> str:
        return self.__questFormat
    def getQuestColumb(self) -> str:
        return self.__questColumb
    def getQuestIsFinish(self) -> bool:
        return self.__questIsFinish
    
    def setRawAnswer(self,answer) -> bool:
        answerDict = {self.__questColumb:answer}
        self.__pull.setRawAnswer(answerDict)
        return True
    
    #отправляем ответ в questpull, перед этим проверив его 
    def setAnswer(self,answer) -> bool:
        answer =  self.__checkAnswer(answer)
        answerDict = {self.__questColumb:answer}
        
        self.__pull.setAnswer(answerDict)
        self.__questIsFinish = True
        return True
        
    #пропускаем вопрос
    def skipQuest(self) -> bool:
        if self.questCanBeSkiped:
            #здесь раньше передавали questNext
            self.__pull.skipQuest()
            self.__questIsFinish = True
            return True
        else:
            return False
    def backQuest(self) -> bool:
            self.__questIsFinish = True
            self.__pull.backQuest()
            return True

        
    #проверяем вопрос на соответствие типу
    def __checkAnswer(self,answer) -> str:
        if answer == None:
            return False
        while True:
                try:
                    self.setRawAnswer(answer)
                    ##############
                    #если выбор
                    ##############
                    if self.__questType is QuestTypes.Choice:
                        if self.__questVar == None:
                            raise JSONReaderExeption.NoVariantes("Кажется, в опроснике возникли какие-то проблемы.. Свяжитесь с менеджером")
                        return str(answer)
                    ##############  
                    #если текст
                    ##############
                    elif self.__questType is QuestTypes.Text:
                            return str(answer)
                    ##############
                    #если int
                    ##############
                    elif self.__questType is QuestTypes.Int:
                            if answer.isdigit():
                                if self.__questObj.get("range"):
                                    ranged = self.__questObj.get("range")
                                    if int(answer)>ranged["low"] and  int(answer)<ranged["high"]:
                                        return str(answer)
                                    else:
                                        raise JSONReaderExeption.NoConvertInInt("Пожалуйста, проверьте актуальность параметра")
                                else:
                                    return str(answer)
                            else:
                                raise JSONReaderExeption.NoConvertInInt("Немного не так. Пожалуйста, введите число.")
                    ##############
                    #если дата
                    ##############
                    elif self.__questType is QuestTypes.Date:
                        if self._checkDate(answer):
                            try:
                                answer = self._parse_date(answer)
                                if self.__questObj.get("datacheck") == "work":
                                    # Получаем текущую дату
                                    current_date = datetime.now()

                                    # Проверяем, что дата не меньше сегодняшней и не больше чем через год
                                    if not(current_date <= answer):
                                        season_limits = f"от {current_date.strftime('%d-%m-%Y')}"
                                        raise JSONReaderExeption.ErrorFormat(f"Пожалуйста, укажите актуальную дату на текущий сезон. Рамки сезона: {season_limits}")

                                if self.__questObj.get("datacheck") == "birth":
                                    # Получаем текущую дату
                                    current_date = datetime.now()
                                    # Получаем дату 5 лет назад
                                    five_year_later = current_date - timedelta(days=14 * 365.25)

                                    # Проверяем, что дата меньше 5 лет назад
                                    if not(five_year_later >= answer):
                                        raise JSONReaderExeption.ErrorFormat("Исходя из Вашей даты рождения, Вы слишком молоды для устройства на работу, возможно, Вы ошиблись? ")
                                answer = time.mktime(answer.timetuple())
                                if self.__questCheck:
                                    nextDate = self.__pull.getAnswerList()[self.__questCheck["checkBase"]]
                                    integer_value = float(nextDate)
                                    if self.__questCheck["type"] == "low":
                                        if  answer  > nextDate:
                                            return False
                        
                                    elif self.__questCheck["type"] == "big":
                                        
                                        if answer <= integer_value:
                                            raise JSONReaderExeption.ErrorFormat("Дата конца работы была раньше даты начала работы")
                                    else:
                                        raise JSONReaderExeption.ErrorFormat("Кажется, в опроснике возникли какие-то проблемы.. Свяжитесь с менеджером")
                                return str(answer) 
                            except OverflowError as oe:
                                raise JSONReaderExeption.ErrorFormat("Пожалуйста, укажите актуальную дату") 

                        else:
                            raise JSONReaderExeption.NoConvertInInt("Пожалуйста, введите дату в формате 'дд.мм.гггг'")   
                    

                    ##############
                    #если телефонный номер
                    ##############
                    elif self.__questType is QuestTypes.Phone:
                        if self._checkPhone(answer):
                            return str(answer)
                        else:
                            raise JSONReaderExeption.ErrorFormat("Кажется, вы ввели не телефонный номер.")   
                    ##############
                    #если email
                    ##############
                    elif self.__questType is QuestTypes.Email:
                        if self._checkEmail(answer):
                            return str(answer)
                        else:
                            raise JSONReaderExeption.ErrorFormat("Кажется, вы ввели не адрес электронной почты.")  
                    ##############
                    #если социальная сеть(автоматически подставляется не здесь!)
                    ##############
                    elif self.__questType is QuestTypes.Social:
                        return str(answer)
                    ##############
                    #если формат
                    ##############
                    elif self.__questType is QuestTypes.CloseText:
                        if (
                            answer.count('-') == self.__questFormat.count('-') and
                            answer.count(',') == self.__questFormat.count(',') and
                            answer.count('_') == self.__questFormat.count('_') and
                            answer.count('.') == self.__questFormat.count('.') and
                            len(answer) == len(self.__questFormat) and

                            answer.translate(str.maketrans("", "", ",@-_.")).isdigit()
                        ):                            
                            return str(answer)
                        else:
                            raise JSONReaderExeption.ErrorFormat("Кажется, мы ожидали немного не этого:)\n Введите ответ в формате: " + self.__questFormat)   
                        
                except ValueError as e:
                        raise JSONReaderExeption.NoConvertInInt("Немного не так, кажется, ответ должен иметь числовое значение")    
                

    def _parse_date(self, date_str):
        try:    
            possible_format = '%d.%m.%Y'  # Добавьте другие форматы по необходимости

            # Заменяем символы /, \ и _ на точку
            date_str = date_str.replace('/', '.').replace('\\', '.').replace('_', '.').replace('-', '.')
            date_object = datetime.strptime(date_str, possible_format)
            return date_object
        except ValueError:
            pass

            # Если ни один из форматов не сработал
            raise ValueError("Некорректный формат даты")

    def _checkEmail(self,email) -> bool:
    # Паттерн для проверки email
        email_pattern = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')
        # Проверка соответствия строки паттерну
        return bool(re.match(email_pattern, email))
        pass
    
    def _checkDate(self, date_str) -> bool:
        # Паттерн для проверки даты с различными разделителями
        date_pattern = re.compile(r'^\d{2}[./_\-]\d{2}[./_\-]\d{4}$')

        # Проверка соответствия строки паттерну
        return bool(re.match(date_pattern, date_str))
    
    def _checkPhone(self, phone_str) -> bool:
        # Убираем все пробелы из строки
        cleaned_number = re.sub(r'\s', '', phone_str)

        # Паттерн для проверки телефонного номера в формате 11 цифр
        phone_pattern = re.compile(r'^\d{11}$')

        # Проверка соответствия строки паттерну
        return bool(re.match(phone_pattern, cleaned_number))
#раздаёт вопросы, записывает ответы. один на человека
class questPull:
    def __init__(self,dictClass):
        self.id = 0
        self._answerList = {}
        self.dictClass = dictClass
        self._actualQuest = dictClass.getQuest(self.id)
        self._rawanswerList = {}
        
    #отправляем ответы вместе с кастомными полями 
    def getAnswers(self):

        DayOfWork = float(self._answerList["DateofFinish"]) - float(self._answerList["DateofStart"])
        self._answerList.update({"DaysOfWork": DayOfWork})
        self._answerList.update({"QuestingDate": int(time.time())})
        return self._answerList
    


    #геттеры
    def getAnswerList(self):
       return self._answerList
    def getRawAnswerList(self):
       return self._rawanswerList
    def getActualQuest(self):
       return self._actualQuest
   
        
    #возвращает вопрос следующий. если следующего нет - возвращает None
    def giveQuest(self) -> quest:
        if self.id>=len(self.dictClass.getData()):
            return None
        self._actualQuest = self.dictClass.getQuest(self.id)
        return quest(self)
    

    def backQuest(self) -> bool:
        if self.id !=0:
            self.id-=1
        
    def skipQuest(self):
        self.id+=1
        
    #записывает ответ, увеличивает ID
    def setAnswer(self, answer):
        self._answerList.update(answer)
        self.id +=1
        
    def setRawAnswer(self, answer):
        self._rawanswerList.update(answer)
   
    #кастомный просчёт
    def __calculate_age(self,birth_timestamp) -> int:
        current_timestamp = time.time()
        birth_datetime = datetime.fromtimestamp(birth_timestamp)
        current_datetime = datetime.fromtimestamp(current_timestamp)
    
        age = current_datetime.year - birth_datetime.year - ((current_datetime.month, current_datetime.day) < (birth_datetime.month, birth_datetime.day))
        return age

        
#читатель JSON вызывается 1 раз
class JSONQuestReader(Service):
    def __init__(self, path_to_json):
        self.__path_to_json = path_to_json
        self.__data = None
        

    def start(self):
            self.readJSON()
    def readJSON(self):
            with open(self.__path_to_json, 'r', encoding='utf-8') as file:
                    self.__data = json.load(file)

            if len(self.__data) == 0:
                raise JSONReaderExeption.JSONisEmpty("JSON File is Empty")
            for DataEl in self.__data:
                if DataEl.get("type") == "choise" and not DataEl["variant"]:
                    raise JSONReaderExeption.NotCorrectJSONFile(" Кажется, в опроснике возникли какие-то проблемы.. Свяжитесь с менеджером")
                if DataEl.get("type")== "close_text" and not DataEl["format"]:
                    raise JSONReaderExeption.NotCorrectJSONFile(" Кажется, в опроснике возникли какие-то проблемы.. Свяжитесь с менеджером")
                if DataEl.get("baseCollumb")== None:
                    raise JSONReaderExeption.NotCorrectJSONFile(" Кажется, в опроснике возникли какие-то проблемы.. Свяжитесь с менеджером")

     #Отдаёт нам вопрос по id
    def getQuest(self,id):
        if self.__data != None: 
            return self.__data[id]
        else:
            JSONReaderExeption.JSONisEmpty(" Ой, а где же этот опросник?.. Свяжитесь с менеджером")
            pass
    
    #Отдаёт нам quest pull
    def getQuestPull(self) -> questPull:
        return questPull(self)
    
    
    #Отдаёт нам все вопросы
    def getData(self):
        return self.__data
        
