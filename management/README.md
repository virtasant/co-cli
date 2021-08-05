## Summary

The Virtsant Cloud Optimization platform is a comprehensive solution for optimizing cloud infrastructure.  

This document describes VIRT-CO, the Virtasant command-line interface (CLI) tool for managing customer account access for the purposes of conducting a diagnostic of cloud spend.

This procedure is for diagnostic purposes only, and will grant read-only access to specified accounts.  The instructions below include the procedure to both grant read-only access to the platform and remove that access.


## Overview

The diagram below describes the basic structure of the optimization platform.  Our cloud-based solution accesses cloud metrics and usage information via cross-account access (read-only) to gather standard cloud metrics and usage information.  

For purposes of the diagnostic, we will only access standard AWS metrics, specifically those stored in CloudWatch and CloudTrail.  The solution can also pull from additional AWS data sources (CUR, etc.) as well as 3rd party monitoring tools (Prometheus, Instana, etc.). 


## Script Installation


### Requirements

To install and use the script, the following requirements have to be met:



* Python >= 3.7 installed on the machine
* Pip >= 20.1.1 installed on the machine
* Access to the internet to download additional dependencies (e.g. python libraries)


### Steps

In order to ensure that the running of this script does not interfere with other processes that may be running on your computer, we suggest running the script in its own virtual environment. The main purpose of Python virtual environments is to create an isolated environment for Python projects. This means that each project can have its own dependencies, regardless of what dependencies every other project has. If you are already familiar with this and are already operating within a virtual environment you can skip to the [next](#bookmark=id.urexgqaa8rw8) section.


#### Virtual Environment Setup

Since you are using Python 3, you should already have the [venv](https://docs.python.org/3/library/venv.html) module from the standard library installed. If you do not you will need to install it using the following command:


```
$ pip install virtualenv
```


Once you have done this, please create a new directory to work with as follows:


```
$ mkdir virtasant-co && cd virtasant-co
```


Create a new virtual environment inside the directory. Please note that by default, this will not include any of your existing site packages.


```
$ python3 -m venv .vco
```


In order to use this environment’s packages/resources in isolation, you need to “activate” it. To do this, just run the following:


```
$ source .vco/bin/activate
```


Assuming you have executed all the steps above correctly you should now see the command line prompt change to the following:


```
(vco) $ 
```


Please note that once you are done with running the script you can deactivate this environment using the ‘deactivate’ command as follows:


```
(vco) $ deactivate
```



#### Script Installation

It is wise to make sure you are running the latest version of pip before installing the script. Type the following at the command prompt to upgrade pip:


```
(vco) $ python3 -m pip install --upgrade pip;pip install requests;mkdir manager;cd manager
```


Finally, you are ready to install the cli manager script:


```
(vco) $ wget https://raw.githubusercontent.com/virtasant/co-cli/main/management/apiKeyGen.py
```


This will download a file named apiKenGen.py which you will use to create and manage users with. To get help at any time type the following command:


```
(vco) $ python apiKeyGen.py --help
```


Prior to using the script you will have to create a file called ‘apikey.txt’ which you will populate with a key you get from OPS - which will unlock the functionality you need. This file must reside in the same directory as the script itself. The file will contain one line and its syntax will look something like this:


```
o98h5qwYC67OUqdRsDuem3j8745UGoba64uEYRDI
```



### Using the python script

There are 6 ‘read’ type requests and 2 ‘write’ type ones. The 6 ‘read’ requests are as follows:


```
(vco) $ python apiKeyGen.py --mtok
(vco) $ python apiKeyGen.py --diags
(vco) $ python apiKeyGen.py --customers
(vco) $ python apiKeyGen.py --customer <customer>
(vco) $ python apiKeyGen.py --ctok <customer>
(vco) $ python apiKeyGen.py --cstatus <customer>
```


The `--mtok` parameter returns the master token - a token that is NOT meant to be used by customers - but rather by the customer account manager for accessing the customer data.

The `--diags `parameter will return a list of currently provisioned diagnostic accounts that can be assigned to new or existing customers.

The `--customers `parameter will return a list of all currently provisioned customers.

The next three parameters require the specification of a customer name - and provide detailed information about the customer as follows:



* `--customer` returns a superset of all customer data for the specified customer
* `--ctok `returns a list of the respective customer users and respective tokens
* `--cstatus `returns the provisioning status of the specified customer

The 2 ‘write’ requests are as follows


```
(vco) $ python apiKeyGen.py --provision <user>@<customer>[:<diag>]
(vco) $ python apiKeyGen.py --unprovision <customer>
```


The `--provision` parameter is used to provision a new user@customer and optimally specify which diagnostic account will be used for this customer. The syntax is user@customer where user is a name like Joe and customer is the tld for the customer like acme.com. Optionally, you can add an diagnostic infrastructure account as follows:


```
(vco) $ python apiKeyGen.py --provision joe@acme.com:Diag3
```


Please note that the same (or new) user can be reprovisioned with a different diagnostic infrastructure account as below - resulting in Diag4 being used for ALL users of customer acme.com. Note as well that the diagnostic account name must be in the set returned using the `--diags` parameter.


```
(vco) $ python apiKeyGen.py --provision joe@acme.com:Diag4
```


The `--unprovision `parameter removes the customer and all provisioned user keys associated with this customer.
