import uuid
from http_parser import HttpParser

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

class InfraHttpEventParser(HttpParser):

    def __init__(self, event): super().__init__(event, 'infra')

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
            "status": {
                "default": "pending",
                "Description": "The provisioning status of AWS account.",
                "values" : ["pending", "in-progress","ready-for-use","in-use"]
            },
            "iam" : {
                "aws_access_key_id": "AKIAXXXXXXXXX", 
                "aws_secret_access_key": "BqKIXXXXXXXXXXXXXXX",
                "region": "eu-west-1",
                "cross_account_role": "yet to be provisioned" 
            },
            "jira" : {
                "fqdn": "yet to be provisioned",
                "wiki": "yet to be provisioned",
                "users" : [ 
                    {
                        "username": "admin",
                        "password": "yet to be provisioned"
                    }            
                ]
            },
            "creation_date": "yet to be provisioned",
            "modification_date": "yet to be provisioned"
        }
 
######################################
#    MANDATORY OVERRIDE FROM PARENT  #
######################################
        
    def valid_operations(self):
        return ["GET", "DELETE", "POST", "PUT"]
        
######################################
#    OPTIONAL OVERRIDE FROM PARENT   #
######################################

    def get_search_parameter(self):
        return { 'ready_to_use': { 'status.default' : 'ready-to-use'}}

    def postprocess_event(self, request_state):
        super().postprocess_event(request_state)
        self.filter_response('key', 'name','account') 
