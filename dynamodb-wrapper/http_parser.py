#!/usr/bin/python

import json
import boto3

from event_parser import EventParser, RequestState
from utils import current_date, get_item_from_ddb, rec, update_current_date 
from utils import key_val_from_key_name_and_key_val_arrays, is_one_of_list_in_list
from utils import key_name_in_event_item, get_vals,del_event_item
from utils import preprocess_event_item, process_event_item, nested_get
from utils import is_one_of_list_in_prefix_list, create_prefix_list
from utils import create_nested_dict, parse_hash_mark, get_key_dict, current_date_number
 
#############################################################################
#############################################################################
#############################################################################

class HttpParser(EventParser): 

    def __init__(self, event, table):
        super().__init__(event, table)
        self.a_find_in_response = False
        self.a_filter_response = False
        self.a_body = event['body']
        self.a_headers = event['headers']
        self.a_parameters = event['queryStringParameters']
        self.a_operation = event['requestContext']['httpMethod']
        self.a_payload = self.body()

    def body(self):
        return json.loads(self.a_body) if self.a_body is not None else None

    def reload(self):
        self.a_body = self.a_event['body']
        self.a_parameters = self.a_event['queryStringParameters']
        self.a_operation = self.a_event['requestContext']['httpMethod']
        self.a_payload = self.body()

######################################
 
    # if it gets here it is a valid request
    def preprocess_event(self, request_state):
        if self.a_operation == "POST":
            new_item = self.add_to_item_structure()
            new_item.update({"timestamp": self.get_timestamp()}) 
            new_item.update({"modification_date": current_date()})
            self.a_payload['Item'] = self.preprocess_new_event_item(self.item(), new_item)

        else:
            if self.a_operation in ("PUT", "DELETE"):
                item = self.item()
                if self.a_operation == "PUT":
                    rec(update_current_date, item) 
                k,v = self.key_val_tuple()
                kv_dict = key_val_from_key_name_and_key_val_arrays(k,v)
                ddb = rec(get_item_from_ddb, kv_dict, self.a_ddb)
                ddb_item = rec(preprocess_event_item,ddb['Items'], item, k, v)
                self.a_payload['Item'] = ddb_item 
        return super().preprocess_event(request_state)

######################################

    # if it gets here it is a valid request
    def process_event(self, request_state):
        if self.a_operation == "GET": self.process_get(request_state)
        elif self.a_operation == "POST": self.process_post(request_state)
        elif self.a_operation == "PUT" : self.process_put(request_state)
        elif self.a_operation == "DELETE": self.process_delete(request_state)

######################################

    # if it gets here it is a valid request
    def process_get(self, request_state):
        no_key = [  RequestState.KEY_NAME_NOT_FOUND_IN_REQUEST, 
                    RequestState.KEY_VALUE_NOT_FOUND_IN_REQUEST]
        if request_state in no_key:
            ddb_item = self.a_ddb.scan() 
            if 'Items' in ddb_item:
                items = ddb_item['Items']
                self.update_return_item_with_count(len(items), items)
            else:
                self.update_err_return_message(404, "Table is empty")
        else:
            items = self.get_ddb_event_item()['Items']
            self.update_return_item_with_count(len(items), items)

######################################

    # if it gets here it is a valid request
    def process_post(self, request_state):
        self.a_ddb.put_item(Item=self.item())
        message = "Item posted correctly"
        items = self.get_ddb_event_item()['Items']
        self.update_return_item_with_count(len(items), items)

######################################

    # if it gets here it is a valid request
    def process_delete(self, request_state):
        k,v = self.key_val_tuple()
        count = len(self.item())
        rec(del_event_item,self.item(),self.a_ddb,k)
        message = "Item deleted successfuly"
        self.update_ok_return_message_with_count(count,message)

######################################

    # if it gets here it is a valid request
    def process_put(self, request_state):
        k,v = self.key_val_tuple()
        item = self.item()
        count = len(item)
        event_item = rec(process_event_item,item,self.a_ddb,k,v)
        self.update_return_item_with_count(count,event_item)

######################################
#     REQUIRED OVERRIDE FROM PARENT  #
######################################

    def is_valid_request(self, request_state, overlook):
        if request_state == RequestState.OPERATION_NOT_VALID:
            return super().is_valid_request(request_state, False) 
        elif request_state == RequestState.TABLE_NAME_NOT_FOUND_IN_REQUEST:
            return super().is_valid_request(request_state, False)
        elif request_state == RequestState.KEY_NAME_NOT_FOUND_IN_REQUEST:
            return super().is_valid_request(request_state, self.a_operation == "GET")
        elif request_state == RequestState.KEY_VALUE_NOT_FOUND_IN_REQUEST:
            return super().is_valid_request(request_state, self.a_operation  in ["GET"])
        elif request_state == RequestState.DIIF_LEN_KEY_AND_VALUE_IN_REQUEST:
            return super().is_valid_request(request_state, self.a_operation not in ["POST"])
        elif request_state == RequestState.KEY_NOT_FOUND_IN_DB:
            return super().is_valid_request(request_state, self.a_operation == "POST")
        elif request_state == RequestState.KEY_FOUND_IN_DB:
            return super().is_valid_request(request_state, self.a_operation != "POST")
        else:
            return True

    ###########################

    def is_valid_event(self):
        if "httpMethod" in self.a_event:
            if self.a_operation not in self.valid_operations():
                return self.invalid_operation_in_request()
            else:
                return True
        else:
            self.update_err_return_message(400,"non http request")
            return False

    def respond(self):
        if 'ResponseMetadata' not in self.a_result:
            self.a_result['ResponseMetadata'] = { 'HTTPStatusCode': 200 }
        self.a_result['ResponseMetadata']['HTTPStatusCode'] = self.a_return_code
        self.update_response_message() # allow for modifications by child
        return {
            'statusCode': self.a_return_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': self.encode_json_as_string(self.a_result),  
            "isBase64Encoded": False 
        }
 
    # overwrite in child if you need special processing
    def encode_json_as_string(self, body):
        return json.dumps(body)
        
    def update_response_message(self):
        if self.a_filter_response or self.a_find_in_response:
            del self.a_result['ResponseMetadata']
            if 'count' in self.a_result:
                del self.a_result['count']

######################################

    def table_name_in_request(self):
        if 'queryStringParameters' in self.a_event:
            qsp = self.a_event['queryStringParameters']
            if qsp is not None:
                if 'table' in qsp:
                    if self.a_table is None:
                        self.update_err_return_message(404,'Unrecognized table name')
                        return False
                    else:
                        return True
                else:
                    self.update_err_return_message(404,'No table name specified')
                    return False
            self.update_err_return_message(404,'No table name specified')
            return False
        self.update_err_return_message(404,'No table name specified')
        return False

    # note that key_name is an array
    def key_in_request(self, key_name):
        if self.a_operation in ("PUT", "POST", "DELETE"):
            item = self.item()
            return rec(key_name_in_event_item, self.item(), key_name)
        elif self.a_operation in ("GET"):
            item = self.item()
            #if rec(key_name_in_event_item, self.item(), key_name):
            return True
        else:
            if self.a_parameters is not None:
                # enables customizing the request URL
                parameter_key_name = self.request_parameter_key_name()
                return rec(key_name_in_event_item, self.a_parameters, parameter_key_name)
            else:
                return False

    def key_val_in_request(self, key_name):
        if self.key_in_request(key_name):
            if self.a_operation in ("PUT", "POST", "DELETE", "GET"):
                item = self.item()
                return rec(get_vals, self.item(), key_name) is not None
            else:
                if self.a_parameters is None:
                    return False
                else:
                    # enables customizing the request URL
                    parameter_key_name = self.request_parameter_key_name()
                    if not rec(key_name_in_event_item, self.a_parameters, parameter_key_name):
                        return False
                    else:
                        v = rec(get_vals, self.a_parameters, parameter_key_name)
                        return v is not None and len(v) != 0 #len(parameter_key_name)
        else:
            return False

    def key_val_from_request(self, key_name):
        if self.key_val_in_request(key_name):
            if self.a_operation in ("PUT", "POST", "DELETE", "GET"):
                item = self.item()
                return rec(get_vals, item, key_name)
            else:
                return rec(get_vals, self.a_parameters, self.request_parameter_key_name())
        else:
            return None

    def table_name_not_found_in_request(self, overlook=False):
        self.table_name_in_request()
        return overlook
        
    # can override in child    
    def get_timestamp(self):
        return current_date()
        
######################################
#      HELPER FUNCTIONS.             #
######################################

    def update_err_return_message(self, code, message):
        self.a_return_code = code
        self.a_result = { "Message" : message }

    def update_ok_return_message(self, message):
        self.a_return_code = 200
        self.a_result = { "Message" : message }

    def update_ok_return_message_with_count(self, count, message):
        self.a_return_code = 200
        self.a_result = { "Message" : message }
        self.a_result.update({'count': count})

    def update_return_item(self, message):
        self.a_return_code = 200
        self.a_result = { "Item" : message }

    def update_return_item_with_count(self, count, message):
        self.a_return_code = 200
        self.a_result = { "Items" : message }
        self.a_result.update({'count': count})

    def find_first_occurrence_in_response(self): 
        if "Items" in self.a_result and self.a_parameters is not None and len(self.a_parameters) > 1: 
            items = self.a_result['Items']
            sp = self.get_search_parameter()
            if sp is not None:
                #
                for ksp,vsp in sp.items():
                    if ksp in self.a_parameters:
                        if 'Items' in self.a_result:
                            del self.a_result['Items']
                            self.key_value_not_found_in_db(False)
                        for iksp,ivsp in vsp.items():
                            for item in items: 
                                v = nested_get(item, iksp)
                                if v is not None and v == ivsp: 
                                    kl = self.key_name()
                                    vl = rec(get_vals, item, kl)
                                    kvd = get_key_dict(kl,vl)
                                    self.a_find_in_response = True 
                                    self.a_result.update(kvd) 
                                    if 'Message' in self.a_result:
                                        del self.a_result['Message']
                                    self.a_return_code = 200
                                    return

    def filter_response(self, parameter, *args): 
        if "Items" in self.a_result and self.a_parameters is not None:
            if parameter in self.a_parameters:
                self.a_filter_response = True
                items = self.a_result['Items']
                del self.a_result['Items']
                for item in items:
                    for a in args:
                        v = nested_get(item, a)
                        if v is not None:
                            v = parse_hash_mark(v)
                            self.a_result.update({a : v})        

    def filter_parameter_response(self): 
        if "Items" in self.a_result and self.a_parameters is not None:
            if len(self.a_parameters) > 1: 
                for k,v in self.a_parameters.items():
                    k_params = k.split('.')
                    items = self.a_result['Items']
                    for item in items:
                        v = nested_get(item, k)
                        if v is not None: 
                            v = parse_hash_mark(v)
                            self.a_filter_response = True
                            od = {} 
                            create_nested_dict(k_params, item, v, od)
                            self.a_result.update(od)
                if self.a_filter_response: 
                    if 'Item' in self.a_result:
                        del self.a_result['Item'] 
                    if 'Items' in self.a_result:
                        del self.a_result['Items'] 
                        
    def postprocess_event(self, request_state):
        super().postprocess_event(request_state)
        self.find_first_occurrence_in_response()
        self.filter_parameter_response()

#########################################

    def valid_operations(self):
        return ["GET", "POST", "PUT", "DELETE"]
        
    def get_search_parameter(self):
        return None  
