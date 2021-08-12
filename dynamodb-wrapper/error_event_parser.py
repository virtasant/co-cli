from http_parser import HttpParser


#############################################################################
#############################################################################
#############################################################################

class ErrorEventParser(HttpParser):

    def __init__(self, event): super().__init__(event, None)
    
    def table_name_not_found_in_request(self, overlook=False):
        self.a_return_code = 400
        self.a_result = { "Message" : 'Unsupported event' }
        return overlook
