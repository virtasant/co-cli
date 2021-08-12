import json
import datetime

from utils import update_if_unique
from diagnostics_http_event_parser import DiagnosticsHttpEventParser

#################################

def convert_sf_event_to_body(event):
    f_event = flatten_sf_event(event)
    base_event = create_diagnostics_account_http_base_event(f_event)
    if base_event is not None:

        # see if this record is already in the db
        get_event = create_get_http_event(base_event['qsp'], base_event['body'])
        response = DiagnosticsHttpEventParser(get_event).process()
        new_event = create_sf_diagnostics_account_http_event(base_event, f_event, response)
        if is_new_event(response):
            return create_post_http_event(new_event['qsp'], new_event['body'])
        else:
            return create_put_http_event(new_event['qsp'], new_event['body'])
    return None

#################################

def convert_finders_event_to_body(event):
    f_event = flatten_finders_event(event)
    base_event = create_diagnostics_account_http_base_event(f_event)
    if base_event is not None:

        # see if this record is already in the db
        get_event = create_get_http_event(base_event['qsp'], base_event['body'])
        response = DiagnosticsHttpEventParser(get_event).process()
        new_event = create_finders_diagnostics_account_http_event(base_event, f_event)
        if is_new_event(response):
            return create_post_http_event(new_event['qsp'], new_event['body'])
        else:
            print('***********>>>>>>>>>>> EVENT IS THERE:%s'%(new_event['body']))
            return create_put_http_event(new_event['qsp'], new_event['body'])
    return None

#################################################
#################################################

def set_step_function_status(d, response, status):
    if 'body' in response: 
        body = json.loads(response['body'])
        if status in ['FAILED','ABORTED','TIMED_OUT']:
            d['body']['Item']['step_functions'].update({"status" : status})
        elif 'Items' in body:
            item = body['Items'][0]
            #t = get_time_delta(item['timestamp'])

            l_running = len(item['step_functions']['running'])
            l_succeeded = len(item['step_functions']['succeeded'])

            if l_succeeded == 2 and status == 'SUCCEEDED':
                d['body']['Item']['step_functions'].update({"status" : status})
            else:
                d['body']['Item']['step_functions'].update({"status" : 'RUNNING'})
        else:
            #t = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.00Z")
            d['body']['Item']['step_functions'].update({"status" : 'RUNNING'})
    return d

def get_time_delta(time_str):
    date_time_obj = datetime.datetime.strptime(time_str, '%Y%m%d%H%M%S')
    #return datetime.datetime.now() - date_time_obj
    return date_time_obj.strftime("%Y-%m-%dT%H:%M:%S.00Z")
    
def is_new_event(response):
    if response is not None and 'statusCode' in response:
        status_code = response['statusCode']
        if 404 == status_code and 'body' in response:
            message = json.loads(response['body'])
            key_not_found = "key not found in DB"
            return message is not None and 'Message' in message and message['Message'] == key_not_found
        elif 200 == status_code:
            return False
    return None

########################

def is_finders_event(event):
    e_type = event_type(event)
    e_text = 'API Error Event'
    return e_type is not None and e_type == e_text

########################

def is_diagnostics_event(event):
    e_type = event_type(event)
    e_text = 'Step Functions Execution Status Change'
    return e_type is not None and e_type == e_text

########################

def is_running(e_detail):
    status = event_status(e_detail)
    return status is not None and status == 'RUNNING'

def is_failed(e_detail):
    status = event_status(e_detail)
    return status is not None and status == 'FAILED'

def is_succeeded(e_detail):
    status = event_status(e_detail)
    return status is not None and status == 'SUCCEEDED'

#################################################
#################################################

def create_diagnostics_account_http_base_event(event):
    d = {'qsp': {}, 'body': {}}
    
    d['qsp'] = {"table": "diagnostics"}
    d['body'] = {"Item": {}}
    
    d['body']['Item'].update({"account": event['customer_account']})
    d['body']['Item'].update({"region": event['region']})
    return d

def create_sf_diagnostics_account_http_event(d, event, response):

    d['body']['Item'].update({"step_functions": {}})
    
    status = event['status']
    arn = event['state_machine_account_region_arn']
    sf = d['body']['Item']['step_functions']
    print('******STATUS: %s, URL:%s'%(status,arn)) 

    if status == "RUNNING":
        update_if_unique(sf,"running",arn)
        reset_queues(sf,arn)
    else:                           
        sf.update({"running" : ['-%s'%(arn)]})

    if status == "FAILED":      update_if_unique(sf,"failed",arn)
    elif status == "SUCCEEDED": update_if_unique(sf,"succeeded",arn)
    elif status == "TIMED_OUT": update_if_unique(sf,"timed_out",arn)
    elif status == "ABORTED":   update_if_unique(sf,"aborted",arn)

    return set_step_function_status(d, response, event['status'])

def reset_queues(sf,arn):
    update_if_unique(sf,"failed",'-%s'%(arn))
    update_if_unique(sf,"aborted",'-%s'%(arn))
    update_if_unique(sf,"timed_out",'-%s'%(arn))
    update_if_unique(sf,"succeeded",'-%s'%(arn))

##############################

def create_finders_diagnostics_account_http_event(d, event):

    playbook_error = {}
    playbook_error['checkname'] = event['checkname']
    playbook_error['errorType'] = event['error_type']
    playbook_error['errorMsg'] = event['error_message']
    playbook_error['errorOperation'] = event['error_operation']
    playbook_error['errorEventString'] = event['entry_string']
    d['body']['Item'].update({"playbooks": [playbook_error]})
    print ('create_finders_diagnostics_account_http_event: %s'%(d))
    return d
#################################################
#################################################

def flatten_sf_event(event):
    d = {}
    d['type'] = event_type(event)
    d['source'] = event_source(event)
    d['time'] = event_time(event)
    d['account'] = event_account(event)
    
    e_detail = event_detail(event)
    if e_detail is not None:
        d['status'] = event_status(e_detail)
        d['execution_arn'] = event_execution_arn(e_detail)
        d['state_machine_arn'] = event_state_machine_arn(e_detail)
        d['state_machine_type'] = event_state_machine_type(e_detail)
        d['state_machine_name'] = event_state_machine_name(e_detail)
        d['state_machine_stop_date'] = event_state_machine_stop_date(e_detail)
        d['state_machine_start_date'] = event_state_machine_start_date(e_detail)

        e_input = json.loads(event_input(e_detail))
        if e_input is not None:
            d['region'] = event_region(e_input)
            d['customer_account'] = event_customer_account(e_input)
            d['sqs_queue'] = event_sqs_queue(e_input)
            d['db_schema'] = event_db_schema(e_input)
            d['execution_id'] = event_execution_id(e_input)
            d['datalake_prefix'] = event_datalake_prefix(e_input)
            d['datalake_bucket'] = event_datalake_bucket(e_input)
            d['state_machine_arn_url'] = event_execution_arn_url(d['execution_arn'],d['region'])
            
            region = d['region']
            account = d['customer_account']
            sma = d['state_machine_arn']
            d['state_machine_account_region_arn'] = event_state_machine_account_region_arn(sma,account,region)

    return d
            
def flatten_finders_event(event):
    d = {}
    d['type'] = event_type(event)
    d['source'] = event_source(event)
    d['time'] = event_time(event)

    e_detail = event_detail(event)
    if e_detail is not None:
        d['checkname'] = e_detail['checkname']
        d['region'] = e_detail['region']
        d['customer_account'] = e_detail['customer_account']
        d['role'] = e_detail['role']
        d['provider'] = e_detail['provider']
        d['error_type'] = e_detail['error_type']
        d['error_message'] = e_detail['error_message']
        d['error_operation'] = e_detail['error_operation']
        d['entry_string'] = e_detail['entry_string']
  
    return d            
############################
#### 'event' parameters ####
############################

def event_type(event):
    return event['detail-type'] if 'detail-type' in event else None

def event_source(event):
    return event['source'] if 'source' in event else None

def event_time(event):
    return event['time'] if 'time' in event else None

def event_account(event):
    return event['account'] if 'account' in event else None

def event_detail(event):
    return event['detail'] if 'detail' in event else None

############################
#### 'details' parameters ####
############################

def event_status(detail):
    return detail['status'] if 'status' in detail else None

def event_execution_arn(detail):
    return detail['executionArn'] if 'executionArn' in detail else None
    
def event_execution_arn_url(arn, region):
    return 'https://console.aws.amazon.com/states/home?region=%s#/executions/details/%s'%(region,arn)

def event_state_machine_arn(detail):
    return detail['stateMachineArn'] if 'stateMachineArn' in detail else None
    
def event_state_machine_account_region_arn(sma,account,region):
    return '%s:%s-%s'%(sma,account,region)

def event_state_machine_type(detail):
    arn = event_state_machine_arn(detail)
    return arn.split(":")[-1] if arn is not None else None

def event_state_machine_name(detail):
    return detail['name'] if 'name' in detail else None

def event_state_machine_start_date(detail):
    return detail['startDate'] if 'startDate' in detail else None

def event_state_machine_stop_date(detail):
    return detail['stopDate'] if 'stopDate' in detail else None

def event_input(detail):
    return detail['input'] if 'input' in detail else None

############################
#### 'input' parameters ####
############################

def event_region(e_input):
    return e_input['region'] if 'region' in e_input else None

def event_customer_account(e_input):
    return e_input['Account'] if 'Account' in e_input else None

def event_sqs_queue(e_input):
    return e_input['account'] if 'account' in e_input else None

def event_db_schema(e_input):
    return e_input['db_schema'] if 'db_schema' in e_input else None

def event_execution_id(e_input):
    return e_input['execution_id'] if 'execution_id' in e_input else None

def event_datalake_prefix(e_input):
    return e_input['prefix'] if 'prefix' in e_input else None

def event_datalake_bucket(e_input):
    return e_input['cahce_bucket'] if 'cahce_bucket' in e_input else None

#################################################
#################################################

def create_post_http_event(qsp, body):
    event = {}
    event.update({"queryStringParameters": qsp})
    event.update({"requestContext": {"httpMethod": "POST"}})
    event.update({"body": json.dumps(body)})
    return event


def create_put_http_event(qsp, body):
    event = {}
    event.update({"queryStringParameters": qsp})
    event.update({"requestContext": {"httpMethod": "PUT"}})
    event.update({"body": json.dumps(body)})
    return event

def create_get_http_event(qsp, body):
    event = {}
    event.update({"queryStringParameters": qsp})
    event.update({"requestContext": {"httpMethod": "GET"}})
    event.update({"body": json.dumps(body)})
    return event
