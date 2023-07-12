#!/usr/bin/env python

############# Original description taken from the paramiko ssh connection library demo file.
############# Base file: "paramiko/demos/demo_simple.py" which had the Latest commit c091e75 on May 29, 2018
#  
# Copyright (C) 2003-2007  Robey Pointer <robeypointer@gmail.com>
#
# This file is part of paramiko.
#
# Paramiko is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# Paramiko is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Paramiko; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA.

############# Additional modifications where added to add automation features. 
############# Bringing a hole new software:
############# Automated-SSH


import getpass
import sys
import traceback
from paramiko.py3compat import input

import paramiko


try:
    import automated_ssh_interactive
except ImportError:
    from . import automated_ssh_interactive


# setup logging
paramiko.util.log_to_file("ssh_paramiko.log")

# Paramiko client configuration
UseGSSAPI = (
    paramiko.GSS_AUTH_AVAILABLE
)  # enable "gssapi-with-mic" authentication, if supported by your python installation
DoGSSAPIKeyExchange = (
    paramiko.GSS_AUTH_AVAILABLE
)  # enable "gssapi-kex" key exchange, if supported by your python installation
# UseGSSAPI = False
# DoGSSAPIKeyExchange = False
port = 22

argumentsLen = len(sys.argv)

automated_ssh_logo="""
 _______ _     _ _______ _______     ______ ______ _     _
(_______|_)   (_|_______|_______)   / _____) _____|_)   (_)
 _______ _     _    _    _     _   ( (____( (____  _______
|  ___  | |   | |  | |  | |   | |   \____ \\____ \|  ___  |
| |   | | |___| |  | |  | |___| |   _____) )____) ) |   | |
|_|   |_|\_____/   |_|   \_____/   (______(______/|_|   |_|

"""

usageMessage="""
WARNING: Pass the password as command line parameter should only be done in masked pipelines and It is risky. Use It under your responsibility.

Error parsing the arguments. The required arguments are 'user@host' (as first argument). Watch the example:

python automated_ssh.py user@host password=123 config-file=automated_ssh_config.yaml  port=22 pk=pathToPrivateKeyFile map=myVar:myValue map=myVar2:myValue2

"""


# get hostname
username = ""

if argumentsLen > 1:
    hostname = sys.argv[1]
    if hostname.find("@") >= 0:
        username, hostname = hostname.split("@")
        if hostname.find(":") >= 0:
            hostname, portstr = hostname.split(":")
            port = int(portstr)
    else:
        print (automated_ssh_logo+usageMessage)
        sys.exit(1)

else:
    print (automated_ssh_logo+usageMessage)
    sys.exit(1)


privateKeyFile=""
password=""
configFile="none"

# get additional parameters like port, private key and mapped variables for the automated_ssh_config
if argumentsLen >= 2:
    try:
        for argumentIndex in range(2,argumentsLen):
            argument = sys.argv[argumentIndex]
            if argument.find("=") >= 0:
                argumentName,argumentValue = argument.split("=")
                if argumentName == "config-file":
                    configFile=argumentValue                
                if argumentName == "port":
                    port=argumentValue
                if argumentName == "password":
                    password=argumentValue                    
                if argumentName == "pk":
                    privateKeyFile=argumentValue
                elif argumentName == "map":
                    if argumentValue.find(":") >= 0:
                        mappedVariableName,mappedVariableValue = argumentValue.split(":")
                        automated_ssh_interactive.mappedVariables[mappedVariableName]=mappedVariableValue
        #print("Mapped Variables" + str(automated_ssh_interactive.mappedVariables ))
    except:

        print (automated_ssh_logo+usageMessage)
        sys.exit(1)


#Validate configuration file


missingDynamicInitialCommand=automated_ssh_interactive.validateInitialCommands()
if missingDynamicInitialCommand != "" :
    print (automated_ssh_logo+"Missing mapping for dynamic variable in initial commands: " + missingDynamicInitialCommand)
    sys.exit(1)

missingDynamicAutomatedEventCommand=automated_ssh_interactive.validateAutomatedEventCommands()
if missingDynamicAutomatedEventCommand != "" :
    print (automated_ssh_logo+"Missing mapping for dynamic variable in automated event commands: " + missingDynamicAutomatedEventCommand)
    sys.exit(1)

# get username
if username == "":
    default_username = getpass.getuser()
    username = input("Username [%s]: " % default_username)
    if len(username) == 0:
        username = default_username
if not UseGSSAPI and not DoGSSAPIKeyExchange and privateKeyFile == "" and password=="":
    password = getpass.getpass("Password for %s@%s: " % (username, hostname))


# now, connect and use paramiko Client to negotiate SSH2 across the connection
try:
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())
    print("*** Connecting...")
    if privateKeyFile != "":
        client.connect(
            hostname,
            port,
            username,
            key_filename=privateKeyFile
        )
    elif not UseGSSAPI and not DoGSSAPIKeyExchange:
        client.connect(hostname, port, username, password)
    else:
        try:
            client.connect(
                hostname,
                port,
                username,
                gss_auth=UseGSSAPI,
                gss_kex=DoGSSAPIKeyExchange,
            )
        except Exception:
            # traceback.print_exc()
            password = getpass.getpass(
                "Password for %s@%s: " % (username, hostname)
            )
            client.connect(hostname, port, username, password)

    chan = client.invoke_shell()
    print(repr(client.get_transport()))
    print("*** Here we go!\n")
    returnDataDict=automated_ssh_interactive.interactive_shell(chan,configFile)
    chan.close()
    client.close()

    if int(returnDataDict["exit-code"]) > 0:
        sys.exit(int(returnDataDict["exit-code"]))
    elif int(returnDataDict["exit-code"]) < 0:
        sys.exit(1)

except Exception as e:
    print("*** Caught exception: %s: %s" % (e.__class__, e))
    traceback.print_exc()
    try:
        client.close()
    except:
        pass
    sys.exit(1)