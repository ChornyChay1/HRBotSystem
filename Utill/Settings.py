import os
import json
import logging

from typing import Any




def LoadJSON(file_name: str) -> Any:
    with open(file_name, encoding='utf8') as file:
        return json.load(file)
      
def SaveJSON(file_name: str, data:dict):
    with open(file_name, 'w', encoding='utf8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

def GetFilesJsonFromFolder(path:str) -> list:
    return [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.json')] 

def GetFileName(path:str) -> str:
    return os.path.splitext(os.path.basename(path))[0] 

def CreateFolders(path:str):
    try:
        os.makedirs(path)
    except FileExistsError:
        pass
    
    