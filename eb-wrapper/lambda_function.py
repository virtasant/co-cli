import json
from customers_ddb_stream_parser import CustomersDDBStreamParser

def lambda_handler(event, context):
    print(json.dumps(event))
    CustomersDDBStreamParser().process(event)
