from event_parser_factory import EventParserFactory

####################################################

def lambda_handler(event, context):    
    return EventParserFactory(event).process()
