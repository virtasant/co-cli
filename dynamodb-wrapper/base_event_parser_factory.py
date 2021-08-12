import json

from error_event_parser import ErrorEventParser
from error_http_event_parser import ErrorHttpEventParser

####################################################
    
class BaseEventParserFactory:

    def __init__(self, event):
        self.a_event_parser = self.get_event_parser(event)

    def get_event_parser(self, event):
        print('INCOMING EVENT:%s'%(event))
        if 'queryStringParameters' in event:
            qsp = event['queryStringParameters']
            if qsp is not None:
                if 'table' in qsp:
                    table = qsp['table']
                    return self.create_http_event_parser(event, table)
                else:
                    return ErrorHttpEventParser(event)
            return ErrorHttpEventParser(event)
        elif "Records" in event:
            records == event['Records']
            for record in records:
                if "Sns" in record:
                    sns = record['Sns']
                    if "Message" in sns:
                        message = sns['Message']
                        if "table" in message:
                            table = message['table']
                            return self.create_sns_event_parser(event, table)
                        else:
                            return ErrorEventParser(event)
                    else:
                        return ErrorEventParser(event)
                else:
                    return ErrorEventParser(event)
        elif 'detail-type' in event:
            return self.create_eb_event_parser(event)
        else:
            return ErrorEventParser(event)

    def process(self):
        return self.a_event_parser.process()

    ####################################################
    
    def create_http_event_parser(self, event, table):
        return ErrorHttpEventParser(event)

    def create_sns_event_parser(self, event, table):
        return ErrorEventParser(event)

    def create_eb_event_parser(self, event):
        return ErrorEventParser(event)
