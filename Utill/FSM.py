import inspect
import logging
import time
import os
import json
import asyncio
from typing import Any
from Utill.Settings import CreateFolders, SaveJSON, LoadJSON, GetFilesJsonFromFolder, GetFileName



class FSMHandler:
    def __init__(self, path_strategy:str, logger:logging.Logger, parent_service = None, fabric = None,  time_unload:int = 3600) -> None:
        '''
        path_strategy - папка где будет хранитться последниее состояния
        '''
        self._FSMs:dict[str, FSM] = dict()
        self._exist_FSMs: list[str] = [] 
        self._fabric = fabric   
        self._time_unload = time_unload
        self._logger = logger.getChild("FSM")
        self._parent_service = parent_service

       
 
        self._path_strategy = path_strategy
        CreateFolders(self._path_strategy)
        
        json_files = GetFilesJsonFromFolder(path_strategy)
        for file in json_files:
            self._exist_FSMs.append(str(GetFileName(file)))
    
        pass
    
    def Fabric(self, corutine):
        '''
        corutine - коротина прородитель новых стратегий по имени, принимает id(str) и name(str), если такой стратегии ранее не было name - None,
        Если создать не получиться вернуть None
        '''
        if inspect.iscoroutinefunction(corutine): 
            self._fabric = corutine
        pass
    

    async def UnloadNotWork(self):
        unix_time = int(time.time()) 
        fsm_itemns = dict(self._FSMs)
        
        for id, fsm in fsm_itemns.items():
            if unix_time - fsm._last_time_work >= self._time_unload:
                self._logger.debug(f"Unload not work startegy: \"{fsm.__class__.__name__}\"")
                await self.SaveStrategy(id)
                fsm._id = None
                fsm._handler = None
                await fsm.stop()   
                await fsm._qstop()
                
                del self._FSMs[id]
                
        pass

    async def GetFSM(self, id:str):
        fsm = self._FSMs.get(id)
        if fsm:
            return fsm
       
        if self._fabric is None:
            return None
        

        if str(id) in self._exist_FSMs:
            state_dict = LoadJSON(os.path.join(self._path_strategy, str(id) + ".json"))
            fsm = await self._fabric(id = str(id), name=state_dict.get("strategy"), parent_service = self._parent_service)
            if not fsm:
                return None

            await fsm.start()
            fsm._id = str(id)
            fsm._handler = self
            fsm._logger = self._logger.getChild(id)
                
            if not state_dict.get("method"):
                fsm._fsm = getattr(self, "FirstState")
            else:
                for method in dir(fsm):
                    if inspect.iscoroutinefunction(getattr(fsm, method)):
                        if method == state_dict.get("method"): 
                            fsm._fsm = getattr(fsm, method)
                            try:
                                await fsm.Load(state_dict.get("data", {}))
                            except Exception as e:
                                self._logger.warn(f"Create startegy: \"{fsm.__class__.__name__}\" error: \"{type(e)}\"  text: \"{str(e)}\"")
                                return None
                            break
             
            self._FSMs[str(id)] = fsm
            
            self._logger.debug(f"Create startegy: \"{fsm.__class__.__name__}\", with load data")

            return fsm
            
            
                     
        fsm = await self._fabric(id, name = None, parent_service = self._parent_service)
        if fsm:
            await fsm.start()
            fsm._id = str(id)
            fsm._handler = self
            fsm._logger = self._logger.getChild(id)
            

            self._FSMs[str(id)] = fsm
            self._logger.debug(f"Create startegy: \"{fsm.__class__.__name__}\"")
            
            return fsm
        
        return None
        pass
    


    async def SaveStrategy(self, id:str):
        fsm = self._FSMs.get(id)
        
        if fsm is None:
            return 
        
        data = await fsm.Save()
        
        if data is None:
            return

        state = {"strategy": fsm.__class__.__name__, "method": fsm._fsm.__name__, "data": data}
        SaveJSON(os.path.join(self._path_strategy, str(id) + ".json"), state)
        self._logger.debug(f"Save startegy: \"{fsm.__class__.__name__}\"")
        

    async def SaveStrategys(self):
         for id, fsm in self._FSMs.items():
            if fsm is None:
                continue 
        
            data = await fsm.Save()
        
            if data is None:
                continue

            state = {"strategy": fsm.__class__.__name__, "method": fsm._fsm.__name__, "data": data}
            SaveJSON(os.path.join(self._path_strategy, str(id) + ".json"), state)    
            self._logger.debug(f"Save startegy: \"{fsm.__class__.__name__}\"")
    
    async def stop(self):
        for id, fsm in self._FSMs.items():
            await self.SaveStrategy(id)
            fsm._id = None
            fsm._handler = None
            await fsm.stop()   
            await fsm._qstop()
        self._logger.debug(f"FSMHandler stop")
            


class FSM:
    def __init__(self) -> None:
        self._fsm = getattr(self, "FirstState")    
        self._handler: FSMHandler = None
        self._id: str = None
        self._logger:logging.Logger = None
     
        self._queue = asyncio.Queue()
        self._task = asyncio.get_event_loop().create_task(self._sub_queue())
        
        self._last_time_work = 0
        
        self
        
    async def start(self):
        '''
        Ассихронная функция создания
        '''
        pass

    async def FirstState(self, *args: Any, **kwds: Any):
        '''
        Первое состояние вызываемое при загрузке
        '''
        return None
    
 
    async def _sub_queue(self):
        while True:
            sysm, args, kwds = await self._queue.get()
            
            if sysm is not None:
                break
            
            try:
                await self._fsm(*args, **kwds)
            except Exception as e:
                self._logger.warning(f"End error: \"{type(e)}\"  text: \"{str(e)}\"")
           


    async def __call__(self, *args: Any, **kwds: Any) -> Any:
        self._last_time_work = int(time.time()) 
        await self._queue.put((None,args,kwds))
       

    def SetState(self, newstate):
        '''
        Установить новое состояние 
        пример: self.SetState(self.FirstState)
        '''
        if inspect.iscoroutinefunction(newstate): 
            self._fsm = newstate
        
    async def Save(self) -> dict:
        '''
        Вызываеться когда нужно получить данные для сохранения
        '''
        return None
   
    async def Load(self, data:dict):
        '''
        Вызываеться когда нужно передать данные для загрузки
        '''
        pass

    async def stop(self):
        '''
        Вызываеться когда происходит остановка
        '''
        pass

    
    async def _qstart(self):
        
        pass

    async def _qstop(self):
        await self._queue.put(("stop",None,None))
        await self._task
        pass
    
    
    async def CallSave(self):
        if self._handler is None:
            return 
        if self._id is None:
            return
        
        await self._handler.SaveStrategy(self._id)





 