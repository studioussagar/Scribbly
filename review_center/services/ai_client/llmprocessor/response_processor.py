import json

class LLMResponseProcessor:
    def __init__(self):
        ...
    
    def process_resp(self, resp, expected_schema, expected_schema_score = None, expected_schema_label = None):
        response = self.sanitize_resp(resp)
        if response is None:
            return "No Valid Json Found"
        parsed_resp = json.loads(response)
        if self.validate_res(res= parsed_resp, expected_schema=expected_schema, expected_schema_score= expected_schema_score, expected_schema_label= expected_schema_label):
            return parsed_resp
        return "Invalid Json Structure"

    def sanitize_resp(self,res):
        for i in range(len(res)):
            if(res[i] == "{"):
                x = i
                break
        else:
            return None
        for j in range(len(res)-1,0,-1):
            if(res[j] == "}"):
                y = j
                break
        else:
            return None
        update_res = res[x:y+1]
        return update_res

    def validate_res(self, res, expected_schema, expected_schema_score = None, expected_schema_label = None):
        
        for key in expected_schema:
            if key not in res:
                return False
        for key in expected_schema:
            if not isinstance(res[key],expected_schema[key]):
                return False
        if expected_schema_score is not None:
            for key in expected_schema_score:
                if res[key] < 0 or res[key] > 100:
                    return False
        if expected_schema_label is not None:
            for key,value in expected_schema_label.items():
                value_x = res[key]
                if value_x not in value:
                    return False
        return True
