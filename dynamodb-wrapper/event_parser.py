#!/usr/bin/python

import enum
import boto3
from utils import dynamo, get_val, current_date, update_current_date
from utils import err_if_false, keys_from_key_schema, get_update_params
from utils import key_val_from_key_name_and_key_val_arrays
from utils import get_item_from_ddb, rec, update_ddb_dictionary
from utils import del_key_from_ddb_items, update_key_in_ddb_items

###############################################################

class RequestState(enum.Enum):
   OPERATION_NOT_VALID               = 1
   MALFORMED_REQUEST                 = 2
   TABLE_NAME_NOT_FOUND_IN_REQUEST   = 3
   KEY_NAME_NOT_FOUND_IN_REQUEST     = 4
   KEY_VALUE_NOT_FOUND_IN_REQUEST    = 5
   DIIF_LEN_KEY_AND_VALUE_IN_REQUEST = 6
   KEY_NOT_FOUND_IN_DB               = 7
   KEY_FOUND_IN_DB                   = 8

class EventParser:

    def __init__(self, event, table):
        self.a_event = event
        self.a_table = table
        self.a_return_code = 200
        self.a_result = {}
        self.a_payload = {}
        self.a_ddb = dynamo(table)

    def item(self):
        return get_val(self.a_payload, 'Item')

    def key_name(self):
        client = boto3.client('dynamodb')
        response = client.describe_table(TableName=self.a_table)
        if "Table" in response:
            if "KeySchema" in response["Table"]:
                return keys_from_key_schema(response["Table"]["KeySchema"])
        return None

#########################################

    def is_a_valid_operation(self):
        oper = self.a_operation
        return oper in self.valid_operations() # OVERRIDE IN CHILD

###################

    def table_name_exists_in_event(self):
        return self.table_name_in_request() # OVERRIDE IN CHILD

###################

    def key_name_exists_in_event(self):
        key_name = self.key_name()
        return self.key_in_request(key_name) # OVERRIDE IN CHILD

###################

    def key_value_exists_in_event(self):
        key_name = self.key_name()
        return self.key_val_in_request(key_name) # OVERRIDE IN CHILD
        
###################

    def same_len_key_value_in_event(self):
        if self.key_value_exists_in_event():
            k, v = self.key_val_tuple()
            return len(k) == len(v)
        return False

#########################################

    def key(self):
        key_name = self.key_name()
        key_val = self.key_val_from_request(key_name) # OVERRIDE IN CHILD
        return key_val_from_key_name_and_key_val_arrays(key_name, key_val)

    def key_val(self):
        key_name = self.key_name()
        return self.key_val_from_request(key_name) # OVERRIDE IN CHILD

    def key_val_tuple(self):
        key_name = self.key_name()
        key_val = self.key_val_from_request(key_name) # OVERRIDE IN CHILD

        return key_name, key_val

#########################################

    def key_exists_in_ddb(self):
        if self.key_value_exists_in_event():
            key = self.key()
            comparator = 'eq' if self.a_operation == "POST" else 'begins_with'
            ddb_item = get_item_from_ddb(self.key(),self.a_ddb, comparator)
            return 'Count' in ddb_item and ddb_item['Count'] > 0
        return False

    def get_ddb_event_item(self):
        if self.key_value_exists_in_event():
            comparator = 'eq' if self.a_operation == "POST" else 'begins_with'
            return get_item_from_ddb(self.key(),self.a_ddb, comparator)
        return None

    def process(self):
        request_state = self.get_request_state()
        if self.is_valid_request(request_state, False):
            if self.preprocess_event(request_state):
                self.process_event(request_state)
                self.postprocess_event(request_state)
        return self.respond()

    def get_request_state(self):
        if self.is_a_valid_operation():
            if self.table_name_exists_in_event():
                if self.key_name_exists_in_event():
                    if self.key_value_exists_in_event():
                        if self.key_exists_in_ddb():
                            return RequestState.KEY_FOUND_IN_DB
                        else:
                            #if self.same_len_key_value_in_event():
                            return RequestState.KEY_NOT_FOUND_IN_DB
                            #else:
                                #return RequestState.DIIF_LEN_KEY_AND_VALUE_IN_REQUEST
                    else:
                        return RequestState.KEY_VALUE_NOT_FOUND_IN_REQUEST
                else:
                    return RequestState.KEY_NAME_NOT_FOUND_IN_REQUEST
            else:
                return RequestState.TABLE_NAME_NOT_FOUND_IN_REQUEST
        else:
            return RequestState.OPERATION_NOT_VALID

    def is_valid_request(self, request_state, overlook):
        print_request_state(request_state, overlook)
        if request_state == RequestState.OPERATION_NOT_VALID:
            return self.invalid_operation_in_request(overlook)
        elif request_state == RequestState.TABLE_NAME_NOT_FOUND_IN_REQUEST:
            return self.table_name_not_found_in_request(overlook)
        elif request_state == RequestState.MALFORMED_REQUEST:
            return self.malformed_request(overlook)
        elif request_state == RequestState.KEY_NAME_NOT_FOUND_IN_REQUEST:
            return self.key_name_not_found_in_request(overlook)
        elif request_state == RequestState.KEY_VALUE_NOT_FOUND_IN_REQUEST:
            return self.key_value_not_found_in_request(overlook)
        elif request_state == RequestState.DIIF_LEN_KEY_AND_VALUE_IN_REQUEST:
            return self.diff_len_key_value_in_request(overlook)
        elif request_state == RequestState.KEY_NOT_FOUND_IN_DB:
            return self.key_value_not_found_in_db(overlook)
        elif request_state == RequestState.KEY_FOUND_IN_DB:
            return self.key_already_found_in_db(overlook)
        else:
            return True
 
    ###########################

    def malformed_request(self, overlook=False):
        self.a_return_code = err_if_false(400, overlook)
        self.a_result = { "Message" : 'Malformed payload or request header' }
        return overlook

    ###########################

    def key_name_not_found_in_request(self, overlook=False):
        self.a_return_code = err_if_false(404, overlook)
        self.a_result = { "Message" : 'Malformed or missing primary key name' }
        return overlook

    def table_name_not_found_in_request(self, overlook=False):
        self.a_return_code = err_if_false(404, overlook)
        self.a_result = { "Message" : 'No table name is specified in request' }
        return overlook

    ###########################

    def invalid_operation_in_request(self, overlook=False):
        self.a_return_code = err_if_false(403, overlook)
        self.a_result = { "Message" : 'Unsupported Operation' }
        return overlook

    ###########################
    

    def key_value_not_found_in_request(self, overlook=False):
        self.a_return_code = err_if_false(400, overlook)
        self.a_result = { "Message" : 'Request is missing a key value' }
        return overlook

    ###########################

    def key_value_not_found_in_db(self, overlook=False):
        self.a_return_code = err_if_false(404, overlook)
        self.a_result = { "Message" : 'key not found in DB' }
        return overlook

    ###########################

    def diff_len_key_value_in_request(self, overlook=False):
        self.a_return_code = err_if_false(404, overlook)
        self.a_result = { "Message" : 'Problem with request key' }
        return overlook

    ###########################
   
    def key_already_found_in_db(self, overlook=False):
        self.a_return_code = err_if_false(409, overlook)
        self.a_result = { "Message" : 'key already found in DB' }
        return overlook    

    ###########################

    def request_parameter_key_name(self):
        return ['service','action']

    ###########################

    def update_nested_structures(self,key_name, event_item, ddb_item):
        rec(update_ddb_dictionary, ddb_item, key_name, event_item)        

    ###########################

    def is_valid_event():
        pass

    ###########################

    def respond(self):
        pass

    ###########################
        
    def preprocess_event(self, request_state):
        return True

    ###########################
    
    def process_event(self, request_state):
        pass

    ###########################
    
    def postprocess_event(self, request_state):
        pass

    ###########################
    
    def table_name_in_request(self):
        pass

    ###########################

    def key_in_request(self, key_name):
        pass

    ###########################

    def add_to_item_structure(self):
        pass        

#######################################################
#######################################################

    def preprocess_new_event_item(self, event_item, new_item):
        # k and v are arrays
        k,v = self.key_val_tuple()
        self.update_nested_structures(k,event_item, new_item)
        new_item.update(key_val_from_key_name_and_key_val_arrays(k,v))
        return new_item

####################################################

def print_request_state(request_state, overlook):
    if request_state == RequestState.MALFORMED_REQUEST:
        print('malformed_request, overlook:%d'%(overlook))
    elif request_state == RequestState.KEY_NAME_NOT_FOUND_IN_REQUEST:
        print('key_name_not_found_in_request, overlook:%d'%(overlook))
    elif request_state == RequestState.KEY_VALUE_NOT_FOUND_IN_REQUEST:
        print('key_value_not_found_in_request, overlook:%d'%(overlook))
    elif request_state == RequestState.KEY_NOT_FOUND_IN_DB:
        print('key_value_not_found_in_db, overlook:%d'%(overlook))
    elif request_state == RequestState.KEY_FOUND_IN_DB:
        print('key_already_found_in_db, overlook:%d'%(overlook))
        
#######################################################
#######################################################
