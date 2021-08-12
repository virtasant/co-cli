from customers_ddb_stream_parser import CustomersDDBStreamParser

def lambda_handler(event, context):
    CustomersDDBStreamParser().process(event)
