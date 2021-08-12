import json
from http_parser import HttpParser

from utils import err_if_false, current_date_number
from json_utils import DecimalEncoder

#############################################################################


#############################################################################
#############################################################################
#############################################################################

class CostsHttpEventParser(HttpParser):

    def __init__(self, event): super().__init__(event, 'costs')

    ######################################
    #       OVERRIDE FROM PARENT         #
    ######################################

    def add_to_item_structure(self):
        return { 
            "cost": "0",
            "details": [],
            "regions":[],
            "services":[],
            "modification_date": "yet to be provisioned"
        }
  
######################################
#    MANDATORY OVERRIDE FROM PARENT  #
######################################
        
    def valid_operations(self):
        return ["GET", "POST"]
        
######################################
#    OPTIONAL OVERRIDE FROM PARENT   #
######################################

'''
    def get_timestamp(self):
        return current_date_number()

    def encode_json_as_string(self, body):
        return json.dumps(body, cls=DecimalEncoder)
'''
######################################################################
