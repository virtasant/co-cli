#!/usr/local/python

import boto3
import decimal
from json_utils import DecimalEncoder
import datetime
from time import sleep 
from boto3.dynamodb.conditions import Key
import base64
from botocore.exceptions import ClientError

SM_REGION = "us-east-1"
session = boto3.session.Session()
sm_client = session.client(service_name='secretsmanager',region_name=SM_REGION)

#######################################################

def kms():
    return boto3.resource('kms')

#######################################################
#######################################################

def dynamo(table):
    if table is not None:
        return boto3.resource('dynamodb').Table(table)
    else:
        return None

#######################################################

def get_val(dict, key):
    return dict[key] if dict is not None and key in dict else None

#######################################################

def update_element(i,s,e):
    if e in s:
        i[e] = s[e]

#######################################################

def current_date_number():
    return int(datetime.datetime.now().strftime("%Y%m%d%H%M%S")) 

def current_date():
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S")    

#######################################################

def err_if_false(code, condition = False): 
    return 200 if condition else code

#######################################################

def keys_from_key_schema(keySchema):
    response = []
    for key in keySchema:
        response.append(key["AttributeName"])
    return response
    
def key_val_from_key_name_and_key_val_arrays(key_name, key_val):
    return dict(zip(key_name, key_val)) 
    
####################################################

def get_item_from_ddb(key, ddb, comparator='begins_with'):
    expression = ''
    for k, v in key.items():
        expression = rec(get_expression, v, k, expression)
    exp = rec(filter_expression,expression,key,comparator)
    if isinstance(exp, list):
        exp = exp[0]
    return ddb.query(KeyConditionExpression=eval(exp), ScanIndexForward=True)  

def is_one_of_list_in_list(lista, listb):
    for la in lista:
        if la in listb: return True
    return False

def is_one_of_list_in_prefix_list(lista, listb):
    lb = create_prefix_list(listb)
    return is_one_of_list_in_list(lista, lb)

def create_prefix_list(list):
    rl = []
    for l in list:
        p = l.split('.')[0]
        rl.append(p)
    return rl
    
def remove_from_response(response, lst):
    if 'Items' in response:
        for item in response['Items']:
            remove_from_response(item, lst)
    else:
        for item in lst:
            if item in response:
                del response[item] 

def parse_hash_mark(s,location=1):
    s = DecimalEncoder().to_string(s)
    if '#' in s:
        parts = s.split('#')
        len_of_parts = len(parts)
        if len_of_parts >= location + 1:
            return parts[location] 
        else: 
            return parts[len_of_parts-1]
    else:
        return s
        
def update_if_unique(d, key, val):
    if key not in d:
        d.update({key : [val]})
    elif val not in d[key]:
        d[key].append(val)
        
def get_key_dict(key,val):
    if len(key) != len(val):
        return None
    d = {}
    for i in range(len(key)):
        d.update({key[i] : val[i]})
    return d
#########################################################


#########################################################
#    RECURSIVE FUNCTIONS
#########################################################

def get_expression(v, k, expression):
    if isinstance(v, str):
        return expression + ' & Key("' + k + '").eq("' + v + '")'
    elif isinstance(v, int):
        return expression + ' & Key("%s").eq(%d)'%(k,v)

def filter_expression(expression, key, comparator):
    exp = expression[3:]
    return comparator.join(exp.rsplit('eq', 1)) if len(key) > 1 else exp

def update_key_in_ddb_items(ddb_item, kv_dict):
    ddb_item.update(kv_dict)

def del_key_from_ddb_items(ddb_item, key, d):
    for k in key:
        if k in ddb_item:
            d.update({k:ddb_item[k]})
            del ddb_item[k]

def key_name_in_event_item(event_item, key_name):
    for key in key_name:
        if key in event_item:
            return True
    return False     
    
def get_update_params(body, ddb, k):
    update_expression = ["set "]
    update_names = dict()
    update_values = dict()

    for key, val in body.items():
        key = key.replace('-', '_').replace(' ', '_')
        update_expression.append(f"#{key} = :{key},")
        update_names[f"#{key}"] = key
        update_values[f":{key}"] = val
        
    a, v, n = "".join(update_expression)[:-1], update_values, update_names

    return ddb.update_item(
        Key=k, 
        UpdateExpression=a,
        ExpressionAttributeValues=dict(v),
        ExpressionAttributeNames=dict(n)
    )    

def get_vals(dict, key):
    if dict is not None:
        response = []
        for k in key:
            if k in dict:
                response.append(dict[k])
        return response
    else:
        return None

# key_name is an array of keys
def update_ddb_dictionary(ddb_item,key_name,event_item, depth=0): 
    for k,v in ddb_item.items():   
        if isinstance(v, dict):
            if k in event_item:
                update_ddb_dictionary(ddb_item[k], key_name, event_item[k], depth+1)
        else:            
            if k in event_item and (k not in key_name or depth != 0): 
                if isinstance(v, list):
                    event_item_extra = (list(filter(lambda x:x not in ddb_item[k], event_item[k])))
                    for eie in event_item_extra:
                        if isinstance(eie, str):
                            if eie[0] == '-':
                                if eie[1:] in ddb_item[k]:
                                    ddb_item[k].remove(eie[1:])
                            else:
                                ddb_item[k].append(eie)
                        else:
                            ddb_item[k].append(eie)
                else:
                    ddb_item[k] = event_item[k]


def update_current_date(item):
    item.update({"modification_date": current_date()})


def preprocess_event_item(ddb_item, event_item, k, v):
    
    kv_dict = {}
    del_key_from_ddb_items(ddb_item, k, kv_dict)
    update_ddb_dictionary(ddb_item, k, event_item)        
    update_key_in_ddb_items(ddb_item, kv_dict)
    return ddb_item

def process_event_item(event_item, ddb, k,v):  
    if v is not None:
        if isinstance(v, list) and len(v) != 0:
            val = v[0]
        else:
            val = v
    kv_dict = key_val_from_key_name_and_key_val_arrays(k,val)
    del_key_from_ddb_items(event_item, k, kv_dict)
    get_update_params(event_item, ddb, kv_dict)
    update_key_in_ddb_items(event_item, kv_dict)
    if v is not None:
        if isinstance(v, list) and len(v) > 0: 
            v.pop(0)
    return event_item

def del_event_item(item, ddb, k):
    kv_dict = {}
    for key in k: 
        kv_dict.update({key: get_val(item, key)})
    ddb.delete_item(Key=kv_dict) 

def nested_get(dct, key):
    keys = key.split('.')
    if len(keys) == 1:
        k = keys[0]
        return dct[k] if k in dct else None
    elif isinstance(dct[keys[0]], dict):
        return nested_get(dct[keys[0]], '.'.join(keys[1:]))

#########################################################

def rec(func, item, *args):
    if isinstance(item, list):
        response = []
        for i in item:
            response.append(rec(func, i, *args))
            #sleep(0.2) 
        return response
    else:

        return func(item, *args)
        
def create_nested_dict(key, idict, value, odict):
    k = key[0]
    if len(key) > 1:
        odict.update({k : {}})
        create_nested_dict(key[1:], idict[k], value, odict[k])  
    else:
        odict.update({k : value})

#########################################################
#########################################################
#########################################################

def get_cli_token_secret():

    secret_name = "CLI_API_Token"

    try:
        get_secret_value_response = sm_client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            raise e
    else:
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            return secret
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
            return decoded_binary_secret
