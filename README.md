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

- `management/` - Python script used for provisioning new users
    - `diag-api-key-generator/` - lambda backend for the 'management' script

## Architecture

![plot](./images/diag-flow-components.png?raw=true)
