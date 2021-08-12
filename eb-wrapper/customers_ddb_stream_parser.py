import os
import json 
import boto3
import typing
import decimal
import distutils

from ddb_stream_parser import DDBStreamParser, DecimalEncoder, DecimalDecoder
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

class CustomersDDBStreamParser(DDBStreamParser):

    def __init__(self): super().__init__()

    #################################################
    
    def update_notification_target(self):
        return os.environ['SNS_ARN']

    #################################################
    
    def handle_insert(self, record):
        # implement insert functionality
        # https://virtasant.atlassian.net/browse/COBACKEND-1462
        self.send_customer_account_provisioning_event(record)


    #################################################
    
    def handle_delete(self, record):
        old_image = unmarshal_json(super().handle_delete(record))
        # implement delete functionality

    #################################################
    
    def handle_update(self, record):
        print(f'handle_update: {record}')
        diff_image = unmarshal_json(super().handle_update(record))
        print ('diff:%s'%(diff_image)) 
        # implement update functionality
        
        if 'cross_account_role_creation_status' in diff_image:
            carcs = diff_image['cross_account_role_creation_status']
            if 'default' in carcs:
                state = carcs['default']
                if 'purge' == state:
                    print ('*****deleting customer account') 
                    # https://virtasant.atlassian.net/browse/COBACKEND-1468
                    self.send_delete_account_event(record)
                elif 'in-progress' == state:
                    print ('IMPLEMENT IN PROGRESS') 
                    # https://virtasant.atlassian.net/browse/COBACKEND-1468
                    self.send_customer_account_provisioning_event(record)
                elif 'done' == state:
                    # https://virtasant.atlassian.net/browse/COBACKEND-1470
                    self.send_start_collection_event(record)
                    
    def send_customer_account_provisioning_event(self, record):
        print('send_customer_account_provisioned_event!!!!!!')
        new_image = unmarshal_json(record['NewImage'])
        infra_account_id = new_image['infra']['cloud']['account']
        if isinstance(infra_account_id, decimal.Decimal):
            infra_account_id = str(infra_account_id) 
        print(f'Infra cloud account id: {infra_account_id}')

        customer_event_bus_name = 'customer-events'
        events = boto3.client('events')
        response = events.put_events(
            Entries=[
                {
                    'EventBusName': customer_event_bus_name,
                    'Source': 'customer',
                    'DetailType': 'customer-account-provisioning-event',
                    'Detail': json.dumps({
                        'account': infra_account_id, # infra structure account id
                        'actionDetails':{
                            # 'cache-bucket': '(O) str: default is "co-aws-data-lake-central" or the value from env',
                            # 'prefix': '(O) str: prefix for s3 bucket. default is "aws_data_lakes" or the value from env',
                            'Action': 'AddAccount',
                                    #   'AddAccount steps:'
                                    #   '1. get account type json from s3'
                                    #   '2. nop init schema (it only extracts schema name from parameters)'
                                    #   '3. insert account to db'
                                    #   '4. add sns access changes!'
                                    #   '      for all topics in crossaccountssns the following permission is added: '
                                    #   '         {'
                                    #   '             "TopicArn": topic,'
                                    #   '             "Label": f"Publish_access_for_{account_id}",'
                                    #   '             "AWSAccountId": [account_id],'
                                    #   '             "ActionName": ["Publish"]'
                                    #   '         }'
                                    #   '5. add_buckets_access_changes: updates all s3 datalake buckets policies to give permission to customer account'
                                    #   '6. save or update <account_id>.json in s3 bucket',
                            # 'Type': '(O) str: default is "default" which is defined under account_types s3. Defines db_schema, sqs-queue, cost-schema',
                            'Customer': new_image['name'], # '(M) str: the name of the customer',
                            # 'AccountName': '(O) str: default is the value in "Customer" field',
                            # 'JiraProject': '(O) str: default is the value in "Customer" field',
                            # 'CrossAccountSNS': '(O) list: default is ["ExternalCustomersStackDeploymentMessages", "DataLakeCollectionFailure", "DataLakeCollectionSuccess"]',
                            'Account': new_image['account'], # '(M) str: the customer account id',
                            'COCrossAccountRole': new_image['profile']['role'], # '(O) str: the cross account role name provisioned in customer account',
                        }
                    }, cls=DecimalEncoder),
                },
            ]
        )
        print(f'customer_account_provisioned_event sent: {response}')
        
    def send_start_collection_event(self, record):
        print('send_start_collection_event!!!!!!')
        new_image = unmarshal_json(record['NewImage'])
        print(f"NEW IMAGE: {new_image}") 
        infra_account_id = new_image['infra']['cloud']['account']
        print(f'Infra cloud account id: {infra_account_id}')

        account = new_image.get('account',None) 
        aws_region = new_image.get('aws_region','us-east-1')
        run_finders = new_image.get('auto_run_finders',True)
        
        regions = new_image.get('regions',None)
        if regions is None or len(regions) == 0: regions = all_regions()
        regions = ', '.join(regions)

        entries = [
            {
                'EventBusName': 'customer-events',
                'Source': 'customer-provisioned',
                'DetailType': 'customer-account-provisioned-event',
                'Detail': json.dumps({
                    'account': infra_account_id, # infra structure account id
                    'actionDetails':{
                        'Account': account,
                        'Region': [aws_region],
                        'regions': regions,
                        'ReadResources': True,
                        'UseDataLakeResources': True,
                        'RunFinders': run_finders, 
                        'SkipDataCollection': False,
                        'ReadMetrics': True,
                        'CrossAccount': new_image['profile']['role']
                    }
                }, cls=DecimalEncoder),
            } # for region in new_image['regions']
        ]
        
        print(f'entries -->: {entries}')
        
        events = boto3.client('events')
        response = events.put_events(Entries=entries)
        print(f'customer_account_provisioned_event sent: {response}')
        
    def send_delete_account_event(self, record):
        event = create_event_header(record,
                                    'customer-deleted',
                                    'send_delete_account_event')

        events = boto3.client('events')
        detail = {
            "account" : event["infra-account"], 
            "actionDetails": {"Account": event["customer-account"]}
        }
        entry = event['header']
        entry.update({'Detail': json.dumps(detail, cls=DecimalEncoder)})
        print('customer-deleted: %s'%(entry))
        response = events.put_events(Entries=[entry])
        print(f'send_delete_account_event sent: {response}')
        
                                    
    ###################################################
    
def create_event_header(record, type, message=None):
    if message is not None:
        print(message)
    new_image = unmarshal_json(record['NewImage'])
    infra_account_id = new_image['infra']['cloud']['account']
    print(f'Infra cloud account id: {infra_account_id}')
    customer_event_bus_name = 'customer-events'
    return {
                'header': {
                    'EventBusName': customer_event_bus_name,
                    'Source': 'customer-provisioned',
                    'DetailType': type
                },
                "infra-account":infra_account_id,
                "customer-account":new_image['account']
            }

    ##################################################

def unmarshal_json(payload):
    d = TypeDeserializer()
    return {k: d.deserialize(value=v) for k, v in payload.items()}

    ##################################################
    
def all_regions():
    return ["us-east-1",
            "us-east-2",	
            "us-west-1",	
            "us-west-2",	
            "ap-south-1",	
            "ap-northeast-2",	
            "ap-northeast-3",	
            "ap-southeast-1",	
            "ap-southeast-2",	
            "ca-central-1",	
            "eu-west-1",	
            "eu-west-2",	
            "eu-west-3",	
            "eu-north-1",	
            "sa-east-1",	
            "ap-northeast-1",	
            "eu-central-1",	
            "eu-central-1",	
            "ap-northeast-1",	
            "cn-north-1",	
            "cn-northwest-1",	
            "eu-south-1",	
            "af-south-1",	
            "ap-east-1",	
            "me-south-1"]
    
##############################################################################
##############################################################################
