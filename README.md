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
- `schema/` - GraphQL definitions

## Architecture

![Infrastructure diagram](/deploy/assets/infra_diagram.png?raw=true)


![plot](./images/diag_flow_high_level.png)
