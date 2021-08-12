from costs_http_event_parser import CostsHttpEventParser
from sandbox_http_event_parser import SandboxHttpEventParser
from actions_http_event_parser import ActionsHttpEventParser
from infra_http_event_parser import InfraHttpEventParser
from customers_http_event_parser import CustomersHttpEventParser
from diagnostics_http_event_parser import DiagnosticsHttpEventParser
from error_http_event_parser import ErrorHttpEventParser
from base_event_parser_factory import BaseEventParserFactory

from eb_utils import is_diagnostics_event, is_finders_event
from eb_utils import convert_sf_event_to_body, convert_finders_event_to_body

#################################################### 
    
class EventParserFactory(BaseEventParserFactory):

    def __init__(self, event): super().__init__(event)

    ####################################################
    
    def create_http_event_parser(self, event, table):
        if table == 'sandbox':
            return SandboxHttpEventParser(event)
        elif table == 'actions':
            return ActionsHttpEventParser(event)
        elif table == 'diagnostics':
            return DiagnosticsHttpEventParser(event)
        elif table == "infra":
            return InfraHttpEventParser(event)
        elif table == "costs":
            return CostsHttpEventParser(event)
        elif table == "customers":
            return CustomersHttpEventParser(event)
        else: 
            return ErrorHttpEventParser(event)
