import json
from diagnostics_ddb_stream_parser import DiagnosticsDDBStreamParser

def lambda_handler(event, context):
    print(json.dumps(event))
    DiagnosticsDDBStreamParser().process(event)
