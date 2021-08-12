import json
import logging

from mapper import Mapper
from api_key_gen import ApiKeyManager

###########################################################

logger = logging.getLogger()
logger.setLevel(logging.INFO)  

###########################################################

PROVISION = 'provision'
UNPROVISION = 'unprovision'
CUSTOMERS = 'customers'
CUSTOMER = 'customer'
DIAGS = 'diags'
CUSTOMER_TOKENS = 'ctok' 
MASTER_TOKEN = 'mtok'
CUSTOMER_STATUS = 'cstatus'

###########################################################

def lambda_handler(event, context):
    
    logger.info(f"NEW event: {event}")
    mapper = Mapper(event, context)
    response = RequestProcessor().process(mapper) 
    
    return {
        'statusCode': 200,
        'body': json.dumps(response) if response else ''
    }

###########################################################
###########################################################

class RequestProcessor():

    def process(self, mapper): 
        manager = ApiKeyManager(mapper)
        target = mapper.get('target')
        return self.targets().get(target,self.error)(manager)
      
    #########################
        
    def targets(self):
        
        return {
            PROVISION : self.provision,
            UNPROVISION : self.unprovision,
            CUSTOMERS : self.customers,
            CUSTOMER : self.customer,
            CUSTOMER_TOKENS : self.ctok,
            MASTER_TOKEN : self.mtok,
            DIAGS : self.diags,
            CUSTOMER_STATUS : self.cstatus
        }


    #########################
        
    def provision(self, manager):
        logger.info("target: provision")
        return manager.provision_user()
        
    def unprovision(self, manager):
        logger.info("target: unprovision")
        return manager.unprovision_customer()
    
    def customers(self, manager):
        logger.info("target: customers")
        return manager.get_all_user_names()
        
    def customer(self, manager):
        logger.info("target: customer")
        return manager.get_users()
        
    def ctok(self, manager):
        logger.info("target: ctok")
        return manager.get_user_keys()
        
    def mtok(self, manager):
        logger.info("target: mtok")
        return manager.get_cli_token_secret()
    
    def diags(self, manager):
        logger.info("target: diags")
        return manager.get_infra_list()
        
    def cstatus(self, manager):
        logger.info("target: cstatus")
        return manager.get_user_status()

    def error(self, manager):
        logger.info("target: error")
        return {}
    
####################################################     

