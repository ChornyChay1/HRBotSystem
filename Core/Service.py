import logging
import asyncio
import time
import inspect
from datetime import datetime


from Core.API import Service
from Utill.AsyncHandler import AsyncHandler


class ServiceWarrper:
    def __init__(self, servicehandler, service:Service):
        self._servicehandler = servicehandler
        self._service = service
        self._logger = service._logger
        
        self._asynchandler = AsyncHandler(self._logger)
        
        self._future = None # self._asynchandler.run_await(self.service_run_decor(service))
        
    def start(self):
        return self._asynchandler.run(self._service.start()).result()
    
    def run(self):
        self._future = self._asynchandler.run(self._service.run())
        pass

    def stop(self):
        if self._future:
            self._future.cancel()
            self._future = self._asynchandler.run(self._service.stop()).result()
        self._asynchandler.stop()
        pass
    
    def DayTimeEvent(self):
        self._asynchandler.run(self._service.DayTimeEvent()).result()
    
    def HourTimeEvent(self):
        self._asynchandler.run(self._service.HourTimeEvent()).result()

        
    def __getattr__(self, __name: str):
        
        attribute = getattr(self._service, __name, None)

        if attribute is None:
            raise AttributeError(f"{__name} not found in {self._service.__class__.__name__}")

        if inspect.iscoroutinefunction(attribute):

            return self._asynchandler.getHandler(attribute)
     
        return attribute 
       
        
    



class ServiceHandler:
    def __init__(self, handler: logging.Handler, loglevel:int) -> None:
        self._logger = logging.getLogger("ServiceHandler")
        
        self._logger.setLevel(loglevel) 
        self._logger.addHandler(handler)
        
        self._handler = handler
        self._loglevel = loglevel
        
        self._service: dict[str, ServiceWarrper] = dict()
        
        current_datetime = datetime.now()  

        self._time_hour = current_datetime.hour
        self._time_day = current_datetime.day
    
        
     
    # async def service_run_decor(self, service):
    #     try:
    #         await service.run()
    #     except BaseException as e:
    #         exc_type, exc_obj, exc_tb = sys.exc_info()
    #         service.GetLogger().critical(f"RUN File: \"{os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]}\" Line: \"{ exc_tb.tb_lineno}\" \"{str(e)}\"")

    def GetService(self, name:str)->Service:
        return self._service.get(name)

    def Add(self, service: Service, name: str):
        
        service.GetLogger().addHandler(self._handler)
        service.GetLogger().setLevel(self._loglevel)
     
        servicewarrper = ServiceWarrper(self, service)
        
        
        servicewarrper.start()
        
        if self._service.get(name):
            self._service.get(name).stop()
        
        self._service[name] = servicewarrper
        
    def run(self, corutine):
        return self._asynchandler.run(corutine) 
        
    def Join(self):
        
        for name, service in self._service.items():
            service.run()

        try:
            while True:
                time.sleep(10)
                
                current_datetime = datetime.now()  
                
                if not self._time_day == current_datetime.day:
                    self._time_day = current_datetime.day
                    self._logger.info("Day time event")
                    for name, service in self._service.items():
                        service.DayTimeEvent() 

                if not self._time_hour == current_datetime.hour:
                    self._time_hour = current_datetime.hour
                    self._logger.info("Hour time event")
                    for name, service in self._service.items():
                        service.HourTimeEvent()               

        except KeyboardInterrupt:
            self._logger.info("Keyboard interrupt, stop all work")
           
        except SystemExit:
            self._logger.info("System exit, stop all work")

        except BaseException as e:
            self._logger.critical(f"Exception: \"{str(e)}\"")
            
        finally:
            for name, service in reversed(self._service.items()):
                service.stop()


