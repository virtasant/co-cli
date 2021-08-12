# co-cli

This is the backend implementation to support the cross account permission 
provisioning CLI tool. 

## Tech Stack

- API:
  - API Gateway
  - Lambda function Python
  - RESTful interface
- Database:
  - DBMS: DynamoDB

## Project structure

- `images/` - 'png's used in the README files
- `management/` - Python script used for provisioning new users
    - `diag-api-key-generator/` - lambda backend for the 'management' script
- `dynamodb-wrapper/` - lambda code wrapping DynamoDB (provides a 'schema') housing customers
- `eb-wrapper/` - lambda code listening for DDB streams and creating relevant events

## TODO

Add EventBridge rules and API GW configuration 

## Architecture

![plot](./images/diag-flow-components.png?raw=true)
