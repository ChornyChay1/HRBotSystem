import asyncio
import threading
import concurrent.futures
import logging
from enum import Enum, auto
from typing import Any


class AsyncHandlerException:
    class IsStop(Exception):
        pass

class AsyncHandlerStatus(Enum):
    Start = auto()
    Run = auto()
    Stop = auto()

class AsyncRunHandler:
    '''
    А class for running coroutines as functions
    '''
    def __init__(self, _async, corutine) -> None:
        self._async = _async
        self._corutine = corutine

    def __call__(self, *args: Any, **kwds: Any) -> asyncio.Future:
        return self._async.run_await(self._corutine(*args, **kwds))
    
    def no_await(self, *args: Any, **kwds: Any) -> concurrent.futures.Future:
        return self._async.run(self._corutine(*args, **kwds))
    


class AsyncHandler:
    def __init__(self, logger: logging.Logger = None):
        if logger:
            self._logger = logger.getChild("AsyncHandler")
        else:
            self._logger = None
            
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._work)
        self._thread.start()
        self._status: AsyncHandlerStatus = AsyncHandlerStatus.Start
    
    async def _empty(self):
        try:
            await asyncio.sleep(5)
        except:
            pass
        return None


    async def _caller_corutine(self, corutine, *args: Any, **kwds: Any):
        try:
            await corutine(*args, **kwds)
        except BaseException as e:
            self._logger.critical(f"Exeption at: {e}")

    async def _caller_method(self, method, *args: Any, **kwds: Any):
        try:
            method(*args, **kwds)
        except BaseException as e:
            self._logger.critical(f"Exeption at: {e}")


    def GetLoop(self) -> asyncio.BaseEventLoop:
        return self._loop

    def join(self):
        self._thread.join()

    def status(self)->AsyncHandlerStatus:
        return self._status

    def IsAlive(self) -> bool:
        return self._thread.is_alive()


    def _work(self):

        self._status = AsyncHandlerStatus.Run

        if self._logger:
            self._logger.debug(f"Run async in thread: \"{threading.get_ident()}\"")

        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_forever()

        except BaseException as e:
            if self._logger:
                self._logger.debug(f"Exception: \"{str(e)}\"")

        finally:
            self._status = AsyncHandlerStatus.Stop
            self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            

        if self._logger:
            self._logger.debug(f"Stop async thread: \"{threading.get_ident()}\"")

         
    
    def run(self, corutine) -> concurrent.futures.Future:
        '''
        Handler corutine
        '''
        if not self.IsAlive():
            raise AsyncHandlerException.IsStop("AsyncHandler is stoped")

        if self._logger:
            self._logger.debug(f"Run function: \"{corutine.__name__}\", in: \"{self._thread.ident}\"")
       
        
        return asyncio.run_coroutine_threadsafe(corutine,self._loop)



    def run_await(self, corutine) -> asyncio.Future:
        '''
        Handler corutine on await Future
        '''
        return asyncio.wrap_future(self.run(corutine))            


    def run_method(self, method, *args: Any, **kwds: Any) -> Any:
        '''
        Handler any non await method on this thread


        Warining!!! Method blocking all corutine
        '''
        if not self.IsAlive():
            raise AsyncHandlerException.IsStop("AsyncHandler is stoped")

        if self._logger:
            self._logger.debug(f"Run function: \"{method.__name__}\", in: \"{self._thread.ident}\"")
       

        return asyncio.run_coroutine_threadsafe(self._caller_method(method, *args, **kwds),self._loop).result()


    def getHandler(self, corutine_func) -> AsyncRunHandler:
        if not self.IsAlive():
            raise AsyncHandlerException.IsStop("AsyncHandler is stoped")

        return AsyncRunHandler(self, corutine_func)
    


    def stop(self):
        if not self.IsAlive():
            #raise AsyncHandlerException.IsStop("AsyncHandler is stoped")
            return

        ft = asyncio.run_coroutine_threadsafe(self._empty(),self._loop)
        self._loop.stop()
        ft.cancel()