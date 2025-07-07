import os
import logging
from Core.API import Service

from Core.Service import ServiceHandler
from Utill.Log import LogHandler
from Utill.Settings import LoadJSON,SaveJSON, CreateFolders

from Service.VK import VK
from Service.TG import TG
from Service.DB import DB
from Service.JSONQuestConvert import JSONQuestReader


from StateMachine.Questing import Questing
from StateMachine.Manager import Manager


report_peer_id = None
manager_id_list = []

s_dict = {}
async def CreateStrategy(id: str, name: str, parent_service: Service,  source: str = None):

    id = int(id)    
    if id<0:
        return None
    
    if (parent_service.__class__.__name__ == "TG") and ( id in manager_id_list):
       return Manager(peer_id=int(id), s_dict = s_dict, parent_service=parent_service)

    return Questing(peer_id=int(id), s_dict = s_dict, report_peer_id = report_peer_id)


    return None
        


def TEST_SETTING_FILE():

    CreateFolders("Settings")
    if not os.path.exists(os.path.join("Settings/Manager.json")):
        SaveJSON("Settings/Manager.json", {"peer": 0, "manager": []})    

    if not os.path.exists(os.path.join("Settings/VK.json")):
        SaveJSON("Settings/VK.json", {"access_token": "","group_id": 0})
        
    if not os.path.exists(os.path.join("Settings/TG.json")):
        SaveJSON("Settings/TG.json", {"access_token": ""})
        



def main():
    loghandler = LogHandler()    
    servicehandler = ServiceHandler(loghandler, logging.DEBUG)
    
    TEST_SETTING_FILE()
    manager_info = LoadJSON("Settings/Manager.json")
    global report_peer_id
    global manager_id_list
    report_peer_id = manager_info.get("peer")
    manager_id_list = manager_info.get("manager", [])

    
    
    reader = JSONQuestReader("Settings/quest.json")
    reader.readJSON()
    

    Base = DB("Data/AnketBase.db")
    servicehandler.Add(Base, "DB") 

    vk = VK(LoadJSON("Settings/VK.json"), "Data/VK_STATE", CreateStrategy)
    servicehandler.Add(vk, "VK")

    tg = TG(LoadJSON("Settings/TG.json"), "Data/TG_STATE", CreateStrategy)
    servicehandler.Add(tg, "TG")
    
    
   

    
    s_dict["reader"] =  reader
    s_dict["BD"] = servicehandler.GetService("DB")
    s_dict["VK"] = servicehandler.GetService("VK")
    s_dict["TG"] = servicehandler.GetService("TG")

  
    servicehandler.Join() 
    





    
if __name__ == "__main__":
    main()
