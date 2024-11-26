import json
import os
from typing import List

def json_loader(key: str = None) -> List[dict | list]:
    try:
        current_path = os.path.abspath(os.getcwd())
        json_file_path = os.path.join(current_path, 'utils/assistant_model.json')

        with open(json_file_path, 'r', encoding='utf-8') as file:
            templates = json.load(file)
            if key:
                if isinstance(templates[key], dict):
                    return list(templates[key].values())
                return templates[key]
            else:
                return templates

    except Exception as e:
        print(Exception, e)

