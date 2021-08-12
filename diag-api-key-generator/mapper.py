import json
 
######################################################
### HELPER CLASS USED TO EXTRACT EVENT PARAMETERS ####
######################################################

class Mapper():
    
    def __init__(self, event, context):
        self.a_is_valid = False
        self.a_event = event
        self.a_context = context
        self.a_payload = self.extract_payload(event)

    #########

    def extract_payload(self, event):
        if 'queryStringParameters' in event:
            self.validate_http(event)
            if event.get('httpMethod') == 'GET':
                return event.get('queryStringParameters')
            else:
                return json.loads(event.get('body'))
        elif "Records" in event:
            r0 = event['Records'][0]
            if 'Sns' in r0:
                message = json.loads(r0['Sns'].get('Message'))
                self.validate_sns(message)
                return self.update_sns_message(message)
            elif 's3' in r0:
                message = r0.get('s3')
                self.validate_s3(message)
                return self.update_s3_message(message)
                
        elif "lambda_arn" in event:
            self.validate_sf(event)
        else:
            self.validate_json(event)

        return event
        
    #########
    
    def is_valid(self):
        return self.a_is_valid

    #########

    def validate_s3(self, message):
        self.a_is_valid = True

    #########

    def validate_sns(self, message):
        self.a_is_valid = True
        
        # this is where you can validate a JWT for instance

    #########

    def validate_sf(self, event):
        self.a_is_valid = True

    #########

    def validate_http(self, event):
        self.a_is_valid = True

    #########

    def validate_json(self, event):
        self.a_is_valid = True

    #########

    def update_s3_message(self, message):
        message['s3'] = '1'
        return message

    #########

    def update_sns_message(self, message):
        message['sns'] = '1'
        return message

    #########

    def get(self, param, alternate=None):
        if 'sns' in self.a_payload:
            return self.a_payload.get('ResourceProperties',{}).get(param, alternate)
        else:
            return self.a_payload.get(param, alternate)

    #########

    def event(self): 
        return self.a_event

    #########

    def payload(self): 
        return self.a_payload
    
###########################################################################
###########################################################################

def unflatten(payload):
    result = dict()
    for k, v in payload.items():   
        d = resultDict
        parts = key.split(".")
        for part in parts[:-1]:
            if part not in d: d[part] = dict()
            d = d[part]
        d[parts[-1]] = value
    return resultDict
    
    
###########################################################################
###########################################################################
