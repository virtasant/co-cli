import uuid
import json
from http_parser import HttpParser
from infra_http_event_parser import InfraHttpEventParser

from utils import err_if_false
from json_utils import DecimalEncoder

#############################################################################
'''
    This DynamoDB wrapper lambda expects an AWS API event
    that is proxied from the client. GET, POST, and 
    DELETE are supported.
    
    The table name is defined by this concrete implementation class
    
    the lookup key for GET and DELETE comes from query parameters 
    using the 'key' prameter
    
        https://...?key=foobar
    
    GETting without any parameters will return all elements in the table
    (no paging for now)
    
    POST requests have the following format
    
    {
        "Item" : {
            <primary key name>:<primary key value>
            <item1 key name> : <item1 value>
            <item2 key name> : <item2 value>
            <item3 key name> : <item3 value>
        }
    }

'''

#############################################################################
#############################################################################
#############################################################################

class DiagnosticsHttpEventParser(HttpParser):

    def __init__(self, event): super().__init__(event, 'diagnostics')

    ######################################
    #       OVERRIDE FROM PARENT         #
    ######################################

    '''
        This function enables you to add a specific schema to new items
        being created. Note that for now this will be in ADDITION to 
        what comes in the event. Future versions may override that as well
    '''

    def add_to_item_structure(self):
        return { 
            "account":"not yet provisioned", 
            "region":"not yet provisioned", 
            "step_functions": {
                "status" : "RUNNING",
                "running" : [],
                "failed": [],
                "succeeded": [],
                "timed_out": [],
                "aborted": []
            },
            "playbooks": []
        }

######################################
#    MANDATORY OVERRIDE FROM PARENT  #
######################################
        
    def valid_operations(self):
        return ["GET", "DELETE", "POST", "PUT"]
        
######################################
#    OPTIONAL OVERRIDE FROM PARENT   #
######################################

    def encode_json_as_string(self, body):
        return json.dumps(body, cls=DecimalEncoder)
        
######################################################################
