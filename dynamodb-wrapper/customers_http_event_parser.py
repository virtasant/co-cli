import uuid
import json
from http_parser import HttpParser
from infra_http_event_parser import InfraHttpEventParser

from json_utils import DecimalEncoder
from utils import err_if_false, get_cli_token_secret
 
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

class CustomersHttpEventParser(HttpParser):

    def __init__(self, event): super().__init__(event, 'customers')

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
            "account": "not yet provisioned", 
            "aws_region" : "us-east-1",
            "accounts": [], 
            "actions" : [],
            "regions" : [],
            "infra" :{
                "cloud": {
                    "name":"yet to be provisioned",
                    "account":"yet to be provisioned"
                },
                "jira": {
                    "fqdn": "yet to be provisioned",
                    "wiki":"https://virtasant.atlassian.net/wiki/spaces/OPS/pages/..."
                },
                "status" : {
                    "default":"diagnostics_account_unavailable",
                    "description": "The provisioning status of AWS account.",
                    "values" : ["diagnostics_account_unavailable", "ready-for-use"]
                }
            },
            "profile": {
                "users" : {}, 
        	    "role" : "yet to be provisioned",
        	    "client-id": "yet to be provisioned",
            },
            "cross_account_role_creation_status": { 
                "default": "pending",
                "template": "yet to be provisioned",
                "Description": "The state of customer CLI execution",
                "values" : ["pending", "purge", "in-progress", "done"] 
            },
            "findings" : [
                {
                    "name": "yet to be provisioned",
                    "opp_finding_status": { 
                        "default": "pending",
                        "description": "The state of customer CLI execution",
                        "values" : ["pending", "collecting","finding","done"]
                    },
                    "modification_date": "yet to be provisioned",
                    "cost": [],
                    "opp": []
                }
            ],
            "auto_run_finders": "true", 
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

    def preprocess_event(self, request_state): 
        item = self.item()
        #if 'x-api-key' in self.a_headers:
            #key = self.a_headers['x-api-key']
            #if key != get_cli_token_secret():
            #TODO add api authentication

        if self.a_operation in ("POST"):
            item.update({"profile": { "client-id":str(uuid.uuid4())}})
            update_accounts(item)
        elif self.a_operation in ("PUT"):
            update_accounts(item)
        return super().preprocess_event(request_state) 

    def postprocess_event(self, request_state):
        super().postprocess_event(request_state)
        self.filter_response('cli','infra.status.default','infra.cloud.account','profile.client-id')
        self.filter_response('progress', 'name','account','infra.status.default','profile.client-id','profile.role','cross_account_role_creation_status.default')
        self.filter_response('success', 'name','account','infra.status.default','profile.client-id','cross_account_role_creation_status.default')
        
    def encode_json_as_string(self, body):
        return json.dumps(body, cls=DecimalEncoder)
        
######################################################################

def update_accounts(item):
    if 'account' in item:
        account = item['account']
        if 'accounts' not in item:
            item['accounts'] = [account]
        elif account not in item['accounts']:
            item['accounts'].append(account)
