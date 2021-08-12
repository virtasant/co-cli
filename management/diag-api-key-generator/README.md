This lambda provides the backend for the `../Management/ApiKeyGen.py` local script that is used to manage customers using Diagnostic accounts for cost optimization.

Please note that other than the standard Lambda permissions, you will need to enable read/write access to AWS SecretsManager.

Finally, please note as well that an API GW RESTful endpoint needs to be created to proxy `GET` requests to this lambda.
