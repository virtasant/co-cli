import json
import logging

from mapper import Mapper
from requestProcessor import RequestProcessor as RP

logger = logging.getLogger()
logger.setLevel(logging.INFO)  

def lambda_handler(event, context):
    
    logger.info(f"NEW event: {event}")
    mapper = Mapper(event, context)
    response = RP().process(mapper) 
    
    return {
        'statusCode': 200,
        'body': json.dumps(response) if response else ''
    }
