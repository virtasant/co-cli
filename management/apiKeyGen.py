import json
import pprint
import argparse
import requests

KEY_FILE = "apikey.txt"
URL = "https://49jq5fhjw2.execute-api.us-east-1.amazonaws.com/internal"

##########################################################################
##########################################################################

def get_key():
    a_file = open(KEY_FILE, "r")
    lines = a_file.readlines()
    a_file.close()
    return lines

def main():

    send_request = False
    ap = argparse.ArgumentParser()
    ap.add_argument('--provision', help="used to provision users,customers and infra\nSyntax <user@customer><:infra(optional)>")
    ap.add_argument('--unprovision', help="used to unprovision users and customers\nSyntax <user(optional)@customer>")
    ap.add_argument('--customer',  help="The TLD of the customer whose record you wish to display")
    ap.add_argument('--cstatus',  help="The TLD of the customer whose status you wish to display")
    ap.add_argument('--ctok',  help="The TLD of the customer whose user keys you wish to display")
    ap.add_argument('--customers',  action='store_true', help="A flag that lists all provisioned customers")
    ap.add_argument('--mtok',  action='store_true', help="A flag that gets you the master CLI token")
    ap.add_argument('--diags',  action='store_true', help="A flag that gets you a list of available diag accounts")

    opts = ap.parse_args()
    target = 'err'
    customer = ''
    
    if opts.diags:
        send_reqeust = True
        target = "diags"
    elif opts.mtok:
        send_reqeust = True
        target = "mtok"
    elif opts.customers:
        send_reqeust = True
        target = "customers"
    elif opts.ctok:
        send_reqeust = True
        target = "ctok"
        customer = opts.ctok
    elif opts.cstatus:
        send_reqeust = True
        target = "cstatus"
        customer = opts.cstatus
    elif opts.customer:
        send_reqeust = True
        target = "customer"
        customer = opts.customer
    elif opts.provision:
        send_reqeust = True
        target = "provision"
        customer = opts.provision
    elif opts.unprovision:
        send_reqeust = True
        target = "unprovision"
        customer = opts.unprovision

    if not send_request:
        print ('You need to provide at least one parameter for this script to work.\nPlease use the "--help" flag for further instructions')
    else:
        params = {'target':target, 'customer':customer}
        headers = {'x-api-key':get_key()[0][:-1]}
        response = requests.get(URL,headers=headers,params=params)

        pprint.pprint(response.json())

if __name__ == '__main__':
    main()
