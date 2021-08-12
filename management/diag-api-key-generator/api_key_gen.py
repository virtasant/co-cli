import os
import sys
import json
import uuid
import boto3
import base64
import logging
import datetime

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from boto3.dynamodb.types import TypeDeserializer

YTBP = "yet to be provisioned"
OUTPUT_FILE = 'key.txt'
CUST_DDB_TABLE = 'customers'
INFRA_DDB_TABLE = 'infra'
USAGE_PLAN_ID = 'fnup9w'
REGION = os.environ.get('REGION', 'us-east-1')

logger = logging.getLogger()
logger.setLevel(logging.INFO)  

deserializer = TypeDeserializer()

session = boto3.Session(region_name=REGION)
ddb_client = session.client('dynamodb')
apigw_client = session.client('apigateway')
sm_client = session.client(service_name='secretsmanager',region_name=REGION)
ddb_infra = boto3.resource('dynamodb', region_name=REGION)
infra_table = ddb_infra.Table(INFRA_DDB_TABLE)

##########################################################################
##########################################################################

def unmarshal(payload):
    return {k: deserializer.deserialize(value=v) for k, v in payload.items()}    

def unmarshal_list(payload):
    return [unmarshal(i) for i in payload]

##########################################################################
    
def is_user_in_users(users, user=None):    
    return users[user] if user and user in users else None
    
##########################################################################

def new_customer_schema(**kwargs):
    user = { 'M' : {} }
    if 'user' in kwargs['profile']['users']:
        user = { 'M' :
                   {
                       kwargs['profile']['users']['user']: {'M' :
                           kwargs['profile']['users']['data']}
                   }
               }
    return {
      'name' : {'S': kwargs['name']},
      "account": {'S' : "not yet provisioned"}, 
      "aws_region" : {'S' : "us-east-1"},
      "accounts": {'L' : []}, 
      "actions" : {'L' : []},
      "regions" : {'L' : []},
      "findings" : {'L' : []},
      "auto_run_finders": {'BOOL' : True }, 
      "modification_date": {'S' : "yet to be provisioned"},
      "timestamp": {'S' : datetime.datetime.now().strftime("%Y%m%d%H%M%S")},
      "profile": { 'M' : 
          {
              "users" : user,
              "role" : {'S' : "yet to be provisioned"},
              "client-id": {'S' : str(uuid.uuid4())}
          }
      },
      "cross_account_role_creation_status": { 'M' : 
          { 
              "default": {'S' : "pending"},
              "template": {'S' : "yet to be provisioned"},
              "Description": {'S' : "The state of customer CLI execution"},
              "values" : {'L' : [{'S':"pending"}, {'S':"purge"}, {'S':"in-progress"}, {'S':"done"}]} 
          }
      },
      "infra" : { 'M' : 
          {
              "cloud": { 'M' : 
                  {
                      "name":{'S' : kwargs['infra']['cloud']['name']},
                      "account":{'S' : kwargs['infra']['cloud']['account']}
                  }
              },
              "jira": { 'M' : 
                  {
                      "fqdn": {'S' : kwargs['infra']['jira']['fqdn']},
                      "wiki": {'S' : kwargs['infra']['jira']['wiki']}
                  }
              },
              "status": { 'M' : 
                  {
                      "default":{'S' : kwargs['infra']['status']['default']},
                      "description": {'S' : "The provisioning status of AWS account."},
                      "values" : {'L' : [{'S':"diagnostics_account_unavailable"}, {'S':"ready-for-use"}]}
                  }
              }
          }
      }
    }


##########################################################################
##########################################################################
##########################################################################

class ApiKeyManager():
    def __init__(self, mapper):
        self.init_vars(mapper)

    ##########################################################################

    def init_vars(self, mapper):
        
        self.usage_plan_id = USAGE_PLAN_ID
        self.target = mapper.get('target')
        self.customer = mapper.get('customer')
        self.user = None
        self.infra = None

        if self.target == 'provision':              # syntax is <user>@<customer>:<infra>
            prov = self.customer.split(':')
            self.infra = prov[-1] if len(prov) > 1 else None
            customer = prov[0].split('@')
            if len(customer) == 1: 
                exit('invalid syntax: missing username')
            self.user = customer[0]
            self.customer = customer[1]
            logger.info(f"user: {self.user}, customer: {self.customer}, infra: {self.infra}")
            
        elif self.target == 'unprovision':          # syntax is <customer>
            unprov = self.customer.split('@')
            self.customer = unprov[0]
            if len(unprov) > 1:
                self.user = unprov[0] 
                self.customer = unprov[1]

    ##########################################################################

    def populate_customer_schema_args(self,data):

        user = {}
        if self.user is not None:
            user['user'] = self.user
            user['data'] = data
    
        infra = self.query_infra()
        jira = infra['jira'] if 'jira' in infra else None
        status = infra['status'] if 'status' in infra else None
    
        if 'account' in infra:
            ia = infra['account']
            account = ia.split('#')[-1] if '#' in ia else ia
        else:
            account = YTBP
    
        return {
           'name': self.customer,
           'profile': {
               'users' : user
           }, 
           'infra':{
               'cloud' : {
                   'account' : account,
                   'name' : infra['name'] if 'name' in infra else YTBP
               },
               'jira' : {
                   'fqdn' : infra['jira']['fqdn'] if jira is not None and 'fqdn' in jira else YTBP,
                   'wiki' : infra['jira']['wiki'] if jira is not None and 'wiki' in jira else YTBP
               },
               'status' : {
                   'default' : infra['status']['default'] if status is not None and 'default' in status else 'diagnostics_account_unavailable'
               }
           }
        }

    ##########################################################################

    def get_key_id(self, key_name: str) -> str:
        """
        Retrieves the id of an API Key based on its name. Returns None if the key is not found
        """
        r = apigw_client.get_api_keys(
            limit=1,
            nameQuery=key_name,
            includeValues=False
        )
        if r and ('items' in r) and len(r['items']) > 0:
            return r['items'][0]['id']
        else:
            return None

    ##########################################################################


    def add_api_key(self):
        
        key_name = f'{self.user}@{self.customer}-API-Key'
        key_id = self.get_key_id(key_name)
        api_key = ''

        if key_id is not None:
            logger.error(f"There is already an API Key with the name '{key_name}: {key_id}'")
            return False
        
        #make sure customer exists in the DB
        api_key = str(uuid.uuid4())
        key_id = apigw_client.create_api_key(
            name=key_name,
            description='string',
            enabled=True,
            value=api_key
        )['id']
            
        apigw_client.create_usage_plan_key(
            usagePlanId=self.usage_plan_id, 
            keyId=key_id, 
            keyType='API_KEY'
        )
        
        logger.info(f'API Key for user {self.user}@{self.customer} created : {api_key}. API Key Id: {key_id}')
        return key_name, key_id, api_key

    ##########################################################################

    def remove_api_keys(self):
        """
        Removes the indicated key from the API Gateway
        """

        keys = self.get_user_key_ids()
        key_ids = keys.get('ids',[])
        key_names = keys.get('names',[])
        
        logger.info(f'ids: {key_ids}, names: {key_names}')

        try:
            for key in key_ids:
                logger.info(f'trying to delete: {key}')
                apigw_client.delete_api_key(apiKey=key)
                logger.info(f"API Key {key} deleted")
        except Exception as msg:
            logger.info(f"Oops, could not delete API key: {msg}")

    ##########################################################################

    def del_customer(self):
        """
        deletes a customer from DynamoDB
        """
        logger.info(f"Deleting user {self.customer} from DynamoDB")

        try:
            response = ddb_client.delete_item(
                TableName=CUST_DDB_TABLE, Key={"name" : {'S' : self.customer}})
        except Exception as msg:
            logger.info(f"Oops, could not UNPROVISION user: {msg}")

        return True

    ##########################################################################

    def post_user(self, key_name, key_id, api_key):
        """
        Inserts/updates a customer into DynamoDB
        """
        logger.info(f"Inserting/Updating user into DynamoDB")

        data = {'key_id':  {'S': key_id}, 
               'key_name': {'S': key_name}, 
               'x-api-key': {'S': api_key}}

        kwargs = self.populate_customer_schema_args(data)
        schema = new_customer_schema(**kwargs)

        try:
            response = ddb_client.put_item(
                TableName=CUST_DDB_TABLE, Item=schema)
        except Exception as msg:
            logger.info(f"Oops, could not PROVISION user: {msg}")

        return True

    ##########################################################################

    def update_user_with_infra(self, key_name, key_id, api_key, infra):
        """
        Inserts/updates a customer into DynamoDB
        """
        logger.info(f"Inserting/Updating user into DynamoDB")

        data = {'key_id':  {'S': key_id}, 
               'key_name': {'S': key_name}, 
               'x-api-key': {'S': api_key}}

        kwargs = self.populate_customer_schema_args(data)

        updateExpression = (f'SET #prof.#users.#user = :userVal, '
                            f'#infra.#cloud.#name = :name, '
                            f'#infra.#cloud.#account = :account, '
                            f'#infra.#jira.#fqdn = :fqdn, '
                            f'#infra.#jira.#wiki = :wiki, '
                            f'#infra.#status.#default = :default')

        try:
            response = ddb_client.update_item(
                TableName=CUST_DDB_TABLE,
                Key={'name' : {'S': self.customer}},
                UpdateExpression=updateExpression,
                ExpressionAttributeNames={
                    '#prof': 'profile',
                    '#users': 'users',
                    '#user': self.user,
                    '#infra': 'infra',
                    '#cloud': 'cloud',
                    '#jira': 'jira',
                    '#status': 'status',
                    '#name': 'name',
                    '#account': 'account',
                    '#fqdn': 'fqdn',
                    '#wiki': 'wiki',
                    '#default': 'default'
                },
                ExpressionAttributeValues={
                    ":userVal": {'M': data},
                    ":name": {'S': kwargs['infra']['cloud']['name']},
                    ":account": {'S': kwargs['infra']['cloud']['account']},
                    ":fqdn": {'S': kwargs['infra']['jira']['fqdn']},
                    ":wiki": {'S': kwargs['infra']['jira']['wiki']},
                    ":default": {'S': kwargs['infra']['status']['default']},
                },
                ReturnValues="UPDATED_NEW"
            )
        except Exception as msg:
            logger.info(f"Oops, could not UPDATE user: {msg}")

        return True

    ##########################################################################

    def update_user(self, key_name, key_id, api_key):
        """
        Inserts/updates a customer into DynamoDB
        """
        logger.info(f"Inserting/Updating user into DynamoDB")

        data = {'key_id':  {'S': key_id}, 
               'key_name': {'S': key_name}, 
               'x-api-key': {'S': api_key}}

        updateExpression = 'SET #prof.#users.#user = :userVal'

        try:
            response = ddb_client.update_item(
                TableName=CUST_DDB_TABLE,
                Key={'name' : {'S': self.customer}},
                UpdateExpression=updateExpression,
                ExpressionAttributeNames={
                    '#prof': 'profile',
                    '#users': 'users',
                    '#user': self.user
                },
                ExpressionAttributeValues={
                    ":userVal": {'M': data}
                },
                ReturnValues="UPDATED_NEW"
            )
        except Exception as msg:
            logger.info(f"Oops, could not UPDATE user: {msg}")

        return True

    ##########################################################################

    def get_users(self):
        """
        Retrievs a customer from DynamoDB
        """
        try:
            response = ddb_client.get_item(
                TableName=CUST_DDB_TABLE,
                Key={'name' : { 'S' : self.customer }}
            )
            if 'Item' not in response:
                logger.info(f"customer {self.customer} NOT found in DynamoDB")
                return None
            else:
                return unmarshal(response['Item'])
        except Exception as msg:
            logger.info(f"Oops, could not GET user: {msg}")

    ##########################################################################
    
    def get_user_status(self):
        
        user = {}
        r = self.get_users()
        if r is not None:
            if 'infra' in r and 'cloud' in r['infra']:
                user.update(r['infra']['cloud'])
            status = r.get('cross_account_role_creation_status',{}).get('default','error')
            user['cross_account_role_creation_status'] = status
        return user

    ##########################################################################
    
    def get_user_key_ids(self):
        
        keys = {"ids":[],"names":[]}
        r = self.get_users()
        if r is not None:
            if 'profile' in r and 'users' in r['profile']:
                for k,v in r['profile']['users'].items():
                    keys['ids'].append(v['key_id'])
                    keys['names'].append(v['key_name'])
        return keys

    ##########################################################################
    
    def get_user_keys(self):
        
        user = {}
        r = self.get_users()
        if r is not None:
            if 'infra' in r and 'cloud' in r['infra']:
                user.update(r['infra']['cloud'])
            if 'profile' in r and 'users' in r['profile']:
                user['tokens'] = []
                users = r['profile']['users']
                [user['tokens'].append({k:{'x-api-key':v['x-api-key']}}) for k,v in users.items()]
        return user

    ##########################################################################
    
    def get_user(self):
        response = self.get_users()
        if response is None:
            return None, False
        else:
            if  'profile' in response and 'users' in response['profile']:
                users = response['profile']['users']
                user = is_user_in_users(users, self.user)
                if user is not None:
                    logger.info(f"user {self.user} found in DynamoDB")
                    return user, True
                else:
                    logger.info(f"user {self.user} NOT found in DynamoDB")
                    return None, True
            logger.info(f"customer {self.customer} NOT found in DynamoDB")
            return None, False
    
    ##########################################################################
 
    def get_infra_list(self):
        """
        Retrievs a list of available diagnostic accounts
        """
        paginator = ddb_client.get_paginator('scan')
        parameters = {
          'TableName': 'infra',
          'AttributesToGet': ['name']
        }

        page_iterator = paginator.paginate(**parameters)

        for page in page_iterator:
            items = unmarshal_list(page['Items'])
        return [v for i in items for k,v in i.items()]

    ##########################################################################
 
    def query_infra(self):
        if self.infra is not None:
            response = infra_table.query(
                KeyConditionExpression=Key('name').eq(self.infra)
            )
            return response['Items'][0] if len(response['Items']) > 0 else response['Items']
        else:
            return []

    ##########################################################################
 
    def get_infra(self, name):
        """
        Retrievs a specific diagnostic account
        """
        try:
            response = infra_table.query(
                KeyConditionExpression=Key('name').eq(name)
            )
            if 'Item' not in response:
                logger.info(f"infra {infra} NOT found in DynamoDB")
            else:
                return unmarshal(response['Item'])
        except Exception as msg:
            logger.info(f"Oops, could not GET user: {msg}")

    ##########################################################################
 
    def provision_user(self):
        key_name = key_id = api_key = ""
        user, found = self.get_user()
        if found:
            if user is not None:                    
                key_name = user['key_name']
                key_id = user['key_id']
                api_key = user['x-api-key']
            elif self.user is not None:                                   
                key_name, key_id, api_key = self.add_api_key()
            il = self.get_infra_list()
            if self.infra and self.infra in self.get_infra_list():
                self.update_user_with_infra(key_name, key_id, api_key, self.infra)
            else:
                self.update_user(key_name, key_id, api_key)
        else:
            if self.user is not None:
                key_name, key_id, api_key = self.add_api_key()
            self.post_user(key_name, key_id, api_key)

        return {'key_name':key_name, 'key_id':key_id, 'api_key':api_key}
    
    ##########################################################################
 
    def unprovision_customer(self):
        customer = self.get_users()
        if customer:
            self.remove_api_keys()
            self.del_customer()
            logger.info(f"Removed Customer {self.customer}")
            return {'Status': 'success'}
        return {'Status': 'not found'}
    

            
    ##########################################################################
 
    def get_all_users(self):
        """
        Retrievs all customers from DynamoDB
        """
        try:
            client = boto3.client('dynamodb')
            paginator = client.get_paginator('scan')
            operation_parameters = {
              'TableName': CUST_DDB_TABLE
            }
    
            items = []
            for page in paginator.paginate(**operation_parameters):
                items.extend([unmarshal(i) for i in page['Items']])
            return items
        except Exception as msg:
            logger.info(f"Oops, could not get all customers: {msg}")

    ##########################################################################
    
    def get_all_user_names(self):
        """
        Retrievs all customer names from DynamoDB
        """
    
        names = []
        [names.append(u['name']) for u in self.get_all_users()]
        return names

    ##########################################################################

    def get_cli_token_secret(self):
    
        secret_name = "CLI_API_Token"
    
        try:
            get_secret_value_response = sm_client.get_secret_value(
                SecretId=secret_name
            )

            if 'SecretString' in get_secret_value_response:
                secret = get_secret_value_response['SecretString']
                return secret
            else:
                decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
                return decoded_binary_secret
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'DecryptionFailureException':
                print(e)
            elif e.response['Error']['Code'] == 'InternalServiceErrorException':
                print(e)
            elif e.response['Error']['Code'] == 'InvalidParameterException':
                print(e)
            elif e.response['Error']['Code'] == 'InvalidRequestException':
                print(e)
            elif e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(e)
            

##########################################################################
##########################################################################
