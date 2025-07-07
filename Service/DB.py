from Core.API import Service
from Core.Service import ServiceHandler
from Utill.Log import LogHandler 
import aiosqlite
import os
from shutil import copy2
from datetime import datetime
import calendar

class BaseExeption:
    class NoBaserData(Exception):
        pass

    class BaseNotFound(Exception):
        pass
    
    class NotAllowData(Exception):
        pass
    


class DB(Service):
    def __init__(self, db_file: str)-> None:
        self._db_file = db_file
        
        super().__init__()
        

    async def DayTimeEvent(self):
            backup_dir='backups'
            # Проверяем, существует ли исходный файл
            if not os.path.isfile(self._db_file):
                self._logger.warning('Backup file is not found')
                return

            # Создаем директорию для бэкапа, если она не существует
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)

            # Имя файла для бэкапа с меткой времени
            base_name = os.path.basename(self._db_file)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            backup_name = f"{base_name}.{timestamp}.db"

            # Полный путь к файлу бэкапа
            backup_path = os.path.join(backup_dir, backup_name)

            # Создаем копию файла
            copy2(self._db_file, backup_path)
            self._logger.info(f'Backup {backup_name} create.')

            # Получаем список всех бэкапов, отсортированный по времени создания (от старых к новым)
            backups = sorted([
            file for file in os.listdir(backup_dir) if file.startswith(base_name)
            ], key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)))

            # Если бэкапов больше чем 5, удаляем самые старые
            while len(backups) > 5:
                old_backup = backups.pop(0) # Удаляем первый элемент list - самый старый бэкап
                os.remove(os.path.join(backup_dir, old_backup))
                self._logger.info(f'Old backup {old_backup} del.')


    #подключаемся к базе и создаём таблицу
    async def start(self):
        self._db = await aiosqlite.connect(self._db_file)
        try:
            async with self._db.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            "ID" INTEGER,                    
            "UserID" TEXT,                  
            "FIO" TEXT,
            "Position" TEXT,                            
            "Sex" TEXT,
            "DateOfBirth" INTEGER,
            "Phone" TEXT,                            
            "EMAIL" TEXT,
            "Sity" TEXT,     
            "VK" TEXT,
            "TG" TEXT,
            "Citizenship" TEXT,
            "MBook" INTEGER,
            "NonCriminal" INTEGER,
            "Family" INTEGER,                            
            "Desease" TEXT,
            "Height" INTEGER,
            "Weight" INTEGER,
            "DateofStart" INTEGER,
            "DateofFinish" INTEGER,
            "Exp" TEXT,                            
            "Education" TEXT,
            "DaysOfWork" INTEGER,                            
            "Status" TEXT DEFAULT 'FREE',
            "QuestingDate" INTEGER,                            
            PRIMARY KEY(id)                            
        )
    """):
             pass
            self._logger.info("Start")
        except Exception as e:
            self._logger.info("Error with create table")
            

            
    #Вставляем данные в таблицу
    async def insertData(self, data):
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data.values()])
        sql_query = f"INSERT INTO profiles ({columns}) VALUES ({placeholders});"

        try:
            async with self._db.execute(sql_query, tuple(data.values())):
                pass
            await self._db.commit()
        except Exception as e:
            self._logger.critical(f"Error with insert in table {str(e)}")


    async def stop(self):
        await self._db.close()
        

    async def upsertData(self, search_field, search_key, data):
        try:
            existing_record = await self.searchField(search_field, search_key)

            if existing_record:
                # Если запись существует, обновляем данные
                await self.updateData(search_key, data)
            else:
                # Если записи не существует, вставляем новые данные
                await self.insertData(data)

            self._logger.info(f"Data upserted for record with '{search_field}' value {search_key}")

        except Exception as e:
            self._logger.critical(f"Error with upsert in table {str(e)}")
            

    async def searchField(self, field, key):
        try:
            # Выполняем запрос к базе данных для поиска значения по указанному полю
            sql_query = f"SELECT * FROM profiles WHERE {field} = ?;"
            async with self._db.execute(sql_query, (key,)) as cursor:
                result = await cursor.fetchone()

            # Если найдено хотя бы одно совпадение, возвращаем данные, иначе None
            return result if result else None

        except Exception as e:
            self._logger.critical(f"Error with search in table {str(e)}")
            return None
        
    async def getField(self, field, key):
        try:
            # Выполняем запрос к базе данных для получения значения по указанному полю
            sql_query = f"SELECT {field} FROM profiles WHERE UserID = ?;"
            async with self._db.execute(sql_query, (key,)) as cursor:
                result = await cursor.fetchone()

            # Если найдено хотя бы одно совпадение, возвращаем значение поля как строку, иначе None
            return result[0] if result else None

        except Exception as e:
            self._logger.critical(f"Error with getting field {field} from table: {str(e)}")
            return None
            
        
    async def updateData(self, from_value, new_data):
        try:
            # Выполняем запрос к базе данных для обновления данных
            sql_query = f"UPDATE profiles SET {', '.join([f'{key} = ?' for key in new_data.keys()])} WHERE UserID = ?;"
            await self._db.execute(sql_query, tuple(new_data.values()) + (from_value,))
            await self._db.commit()

            self._logger.info(f"Data updated for record with 'From' value {from_value}")

        except Exception as e:
            self._logger.critical(f"Error with update in table {str(e)}")
            

    async def selectData(self, conditions, conditionsNot,actuality,order_by=None, sort_mode=1,full = True):
        try:
            # Создаем курсор для выполнения запросов
            async with self._db.execute("") as cursor:
                # Формируем SQL-запрос для положительных условий
                sql_query_pos = "SELECT * FROM profiles"
                if conditions:
                    sql_query_pos += f" WHERE {' AND '.join(conditions)}"

                # Формируем SQL-запрос для отрицательных условий
                sql_query_neg = "SELECT * FROM profiles"
                if conditionsNot:
                    sql_query_neg += f" WHERE NOT {' AND '.join(conditionsNot)}"
                sql_query_act = "SELECT * FROM profiles"
                sql_query_act += f" WHERE {actuality}"

                # Объединяем результаты двух запросов с помощью UNION, только если есть оба списка условий
                if conditions and conditionsNot:
                    sql_query = f"{sql_query_pos} INTERSECT {sql_query_neg} INTERSECT {sql_query_act}"
                elif conditions:
                    sql_query = f"{sql_query_pos} INTERSECT {sql_query_act}"
                elif conditionsNot:
                    sql_query = f"{sql_query_neg} INTERSECT {sql_query_act}"
                else:
                    # Если нет условий, возвращаем все строки
                    sql_query = f"SELECT * FROM profiles INTERSECT {sql_query_act}"

                # Добавляем сортировку, если указано поле для сортировки
                if order_by:
                    sql_query += f" ORDER BY {order_by} {'ASC' if sort_mode == 1 else 'DESC'}"

                # Завершаем формирование SQL-запроса
                sql_query += ';'

                # Выполняем SQL-запрос
                await cursor.execute(sql_query)

                # Получаем имена столбцов
                columns = [column[0] for column in cursor.description]
                # Получаем все строки результата
                result_rows = await cursor.fetchall()

                # Преобразуем кортежи в словари, выбирая только нужные поля в зависимости от значения переменной full
                result_dicts = [dict(zip(columns, row)) for row in result_rows]

            if not full:
                selected_fields = ['FIO', 'DateOfBirth', 'Phone', 'DateofStart', 'Sity']
                result_dicts = [{field: row[field] for field in selected_fields} for row in result_dicts]

            return result_dicts
            


        except Exception as e:
            self._logger.critical(f"Error with select in table \"{str(e)}\"")
            return None

    
        
    async def makeMonthReport(self, year):
        try:
            # Создаем курсор для выполнения запросов
            async with self._db.execute("") as cursor:
                # Формируем SQL-запрос
                sql_query = f"SELECT * FROM profiles WHERE strftime('%Y', datetime(DateofStart, 'unixepoch')) = '{year}' AND Status != 'BROKE'"

                # Выполняем SQL-запрос
                await cursor.execute(sql_query)

                # Получаем имена столбцов
                columns = [column[0] for column in cursor.description]
                # Получаем все строки результата
                result_rows = await cursor.fetchall()

                # Преобразуем кортежи в словари
                result_dicts = [dict(zip(columns, row)) for row in result_rows]

                # Создаем словарь для хранения статистики по месяцам
                month_stats = {month: 0 for month in range(1, 13)}

                # Заполняем статистику
                for row in result_dicts:
                    date_of_start = datetime.fromtimestamp(row["DateofStart"])
                    month_stats[date_of_start.month] += 1

                # Преобразуем номер месяца в название (на русском)
                month_stats_formatted = {calendar.month_name[month]: count for month, count in month_stats.items()}

                return month_stats_formatted

        except Exception as e:
            print(f"Error: {e}")
            return None