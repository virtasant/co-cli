import uuid
from http_parser import HttpParser
from utils import remove_from_response

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

class SandboxHttpEventParser(HttpParser):

    def __init__(self, event): super().__init__(event, 'sandbox')

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
        	"state" : {
        		"provisioning" : {
        			"jira" : "pending",
        			"opp_db" : "pending",
        			"vpc" : "pending",
        			"account" : "pending",
        			"finders" : "pending"
        		}
        	},
        	"jira" : {
        		"url" : "yet to be provisioned",
        		"username" : "yet to be provisioned",
        		"password" : "********"
        	},
        	"role" : "yet to be provisioned",
        	"auth-token": "yet to be provisioned",
        	"auto_run_finders": "false",
        	"email" : "yet to be provisioned",
        	"account" : "734056803705",
            "customer_accounts" : [],
            "customer_regions" : [],
            "name":"yet to be provisioned"
        }

######################################
#    MANDATORY OVERRIDE FROM PARENT  #
######################################
        
    def valid_operations(self):
        return ["GET", "DELETE", "POST", "PUT"]
        
######################################
#    OPTIONAL OVERRIDE FROM PARENT   #
######################################

    def preprocess_new_event_item(self, event_item, new_item):
        super().preprocess_new_event_item(event_item, new_item)
        new_item.update({"clientUUIDToken": str(uuid.uuid4())})
        new_item.update({"account": "734056803705"})
        
        # hack until 2/21/21 when I will FIX this
        new_item.update({"auth-token": "XgASuaWDDV2YGOtbTzERg654OE4tP2Y354WdTex2"})

        return new_item

    def preprocess_event_item(self, ddb_item, k, v):
        clientUUIDToken = ddb_item["clientUUIDToken"];
        del ddb_item[k]
        del ddb_item["clientUUIDToken"]
        event_item = self.item()
        super().preprocess_event_item(event_item, new_item)
        self.update_nested_structures(k,event_item, ddb_item)
        ddb_item.update({"clientUUIDToken": clientUUIDToken})

        # hack until 2/21/21 when I will FIX this
        ddb_item.update({"auth-token": "XgASuaWDDV2YGOtbTzERg654OE4tP2Y354WdTex2"})

        return ddb_item 
 
    def preprocess_event(self, request_state): 
        if super().preprocess_event(request_state):
            if self.a_operation in ("POST"):
                item = self.item()
                customer_regions = item['customer_regions']
                new_regions = (list(filter(lambda x:x not in customer_regions, default_regions())))
                item.update({"regions": new_regions})
            return True
        return False

    def postprocess_event(self, request_state):
        super().postprocess_event(request_state)
        self.filter_response('cli', 'account', 'auto_run_finders')

    def update_response_message(self): 
        super().update_response_message()
        remove_from_response(self.a_result, ['auth-token'])
        
####################################

def default_regions():
    return [
            'us-west-2', 
            'us-east-1', 
            'ap-northeast-1', 
            'eu-west-3', 
            'eu-west-1', 
            'ap-southeast-1', 
            'us-east-2', 
            'eu-central-1', 
            'eu-north-1', 
            'us-west-1',
            'ap-southeast-2', 
            'ap-south-1', 
            'ap-northeast-2', 
            'sa-east-1'
    ]
