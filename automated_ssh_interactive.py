############# Original description taken from the paramiko ssh connection library demo file.
############# Base file: "paramiko/demos/interactive.py" which had the Latest commit c091e75 on May 29, 2018

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


import socket
import threading
import sys
from paramiko.py3compat import u
from yaml import safe_load as yaml_safe_load

# windows does not have termios...
try:
    import termios
    import tty

    has_termios = True
except ImportError:
    has_termios = False

#### automated_ssh start

import time
import logging

expectedTextsDictionary={}
initialCommands=[]

asLoggerFormatter= logging.Formatter("%(levelname)s %(asctime)s - %(message)s")
asLogger = logging.getLogger("automated_ssh")
asLoggerHandler = logging.FileHandler("automated_ssh.log")
asLoggerHandler.setFormatter(asLoggerFormatter)
asLogger.addHandler(asLoggerHandler)
asLogger.setLevel(logging.INFO)

startLogMessage= """
--------------------------------------------
--     AUTOMATED SSH PROGRAM STARTED      --
--------------------------------------------
"""

asLogger.info(startLogMessage)

defaultBetweenNewCommandSeconds=0.5

#has_termios = False # Forced in python 2.7 to avoid errors only while debugging
mappedVariables={}

localDataDict={}
localDataDict["exit-code"]=0
exitCommandReceived=False
usingInteractivity=False

globalPendingCommands = []

def validateInitialCommands():

    for initialCommand in initialCommands:
        if initialCommand.startswith("{{"):
            mappedVariableMatch = False
            for mappedVariableName in mappedVariables:
                if initialCommand.strip() == "{{"+mappedVariableName+"}}":
                    mappedVariableMatch = True
            if not mappedVariableMatch:
                return initialCommand.strip()

    return ""

def validateAutomatedEventCommands():
    for expectedText in expectedTextsDictionary:
        for command in expectedTextsDictionary[expectedText]:
            if command.startswith("{{"):
                mappedVariableMatch = False
                for mappedVariableName in mappedVariables:
                    if command.strip() == "{{"+mappedVariableName+"}}":
                        mappedVariableMatch = True
                if not mappedVariableMatch:
                    return command.strip()

    return ""

def processGlobalPendingCommands(chan):
    global exitCommandReceived
    global globalPendingCommands
    while True:
        if len(globalPendingCommands) > 0:
            command = globalPendingCommands.pop(0)
            try:
                chan.send(command)
                #asLogger.info("Sending command: --"+command+"--")
                if command.strip().lower().startswith("exit"):
                    exitCommandReceived=True
            except Exception as e:
                #asLogger.info("ERROR Sending command: --"+command+"--"+str(e))
                asLogger.info("ERROR Sending command --"+ str(e))
        time.sleep(defaultBetweenNewCommandSeconds)
        if exitCommandReceived: # exit input loop in windows
            try:
                sys.stdin.write("\n")
            except:
                pass

def processAutomatedEvent(chan,data):
    global defaultBetweenNewCommandSeconds
    global globalPendingCommands

    expectedTextsToRemove=[]
    expectedTextsToExecuteUnderAsControl=[]

    for expectedText in expectedTextsDictionary:
        if expectedText in str(data) and not expectedText.startswith("_group_"):
            asLogger.info("Detected expected text: --"+expectedText+"--")
            commandsList = expectedTextsDictionary[expectedText][:]
            for newCommand in commandsList:
                commandForLog=newCommand
                for mappedVariableName in mappedVariables:
                    if "{{"+mappedVariableName+"}}" in newCommand:
                        newCommand = newCommand.replace("{{"+mappedVariableName+"}}",mappedVariables[mappedVariableName])

                if newCommand.startswith("_as_control="):
                    asControlLabel, asControlData = newCommand.split("=")
                    if asControlData.find(":") >= 0:
                        asControlCommand,asControlCommandData=asControlData.split(":")
                        if asControlCommand == "set-exit-code":
                            if int(asControlCommandData) < 0 or int(asControlCommandData) > int(localDataDict["exit-code"] ):
                                localDataDict["exit-code"] = asControlCommandData
                                asLogger.info("AS control: set-exit-code --" + asControlCommandData +"-- for expected text --"+expectedText+"--")
                            else :
                                asLogger.info("AS control: REFUSED set-exit-code --" + asControlCommandData +"-- for expected text --"+expectedText+"-- actual exit code:" + str(localDataDict["exit-code"]))
                        elif asControlCommand == "set-between-new-command-seconds":
                            defaultBetweenNewCommandSeconds = int(asControlCommandData)
                            asLogger.info("AS control: set-between-new-command-seconds --" + asControlCommandData +"-- for expected text --"+expectedText+"--")
                        elif asControlCommand == "clear-commands-queue":
                            globalPendingCommands=[]
                            asLogger.info("AS control: clear-commands-queue -- for expected text --"+expectedText+"--")
                        elif asControlCommand == "remove_expected_text":
                            expectedTextsToRemove.append(asControlCommandData)
                            asLogger.info("AS control: remove_expected_text --" + asControlCommandData +"-- for expected text --"+expectedText+"--")
                        elif asControlCommand == "execute_expected_text_commands":
                            expectedTextToExecuteUnderAsControl,condition=asControlCommandData.split("_condition_")
                            if eval(condition):
                                expectedTextsToExecuteUnderAsControl.append(expectedTextToExecuteUnderAsControl)
                                asLogger.info("AS control: execute_expected_text --" + asControlCommandData +"-- for expected text --"+expectedText+"-- OK")
                            else:
                                asLogger.info("AS control: REFUSED execute_expected_text --" + asControlCommandData +"-- for expected text --"+expectedText+"--")

                else:
                    asLogger.info("Queued command: --"+commandForLog.strip()+"-- for expected text --"+expectedText+"--")
                    globalPendingCommands.append(newCommand)

    for expectedText in expectedTextsToRemove:
        try:
            del expectedTextsDictionary[expectedText]
        except Exception as e:
            asLogger.info("ERROR applying AS control: --remove_expected_text-- text: --"+expectedText+"--" + str(e))

    for expectedText in expectedTextsToExecuteUnderAsControl:
        for newCommand in expectedTextsDictionary[expectedText]:
            if not newCommand.startswith("_as_control="):
                globalPendingCommands.append(newCommand)
                asLogger.info("Queued command under _as_control: --"+newCommand.strip()+"-- for expected text --"+expectedText+"--")


def processInitialAutomatedCommands(chan):
    for initialCommand in initialCommands:
        for mappedVariableName in mappedVariables:
            if "{{"+mappedVariableName+"}}" in initialCommand:
                initialCommand=initialCommand.replace("{{"+mappedVariableName+"}}",mappedVariables[mappedVariableName],1)

        asLogger.info("Sending initial command: --"+initialCommand.strip()+"--")
        chan.send(initialCommand)



def readConfig(configFileName):
    with open(configFileName, "r") as configStream:
        try:
            loadedConfig = yaml_safe_load(configStream)

            if "expectedTextListAdditions" in loadedConfig:
                if type(loadedConfig["expectedTextListAdditions"]) is dict:
                    for baseList in loadedConfig["expectedTextListAdditions"]:
                      for newList in loadedConfig["expectedTextListAdditions"][baseList]:
                        loadedConfig["expectedTextsDictionary"][baseList] = loadedConfig["expectedTextsDictionary"][baseList] + loadedConfig[newList]

            return loadedConfig
        except Exception as e:
            print("Error reading yaml config file" + str(e))
            sys.exit(1)


#### automated_ssh end

def interactive_shell(chan,configFileName):

    #asLogger.info("Arguments used: "+ str(sys.argv))
    #asLogger.info("Mapped Variables: " + str(mappedVariables))

    global initialCommands
    global expectedTextsDictionary
    global usingInteractivity

    if configFileName != "none":
        automated_ssh_config=readConfig(configFileName)
        #automated_ssh_config=importlib.import_module(configFileName)

        if "initialCommands" in automated_ssh_config:
            if type(automated_ssh_config["initialCommands"]) is list:
                initialCommands = automated_ssh_config["initialCommands"]

        if "expectedTextsDictionary" in automated_ssh_config:
            if type(automated_ssh_config["expectedTextsDictionary"]) is dict:
                expectedTextsDictionary = automated_ssh_config["expectedTextsDictionary"]
    else:
        initialCommands = []
        expectedTextsDictionary = {}
        usingInteractivity=True

    if has_termios:
        posix_shell(chan)
    else:
        windows_shell(chan)

    return localDataDict


def posix_shell(chan):
    import select

    commander = threading.Thread(target=processGlobalPendingCommands, args=(chan,))
    commander.daemon = True
    commander.start()

    oldtty = termios.tcgetattr(sys.stdin)
    try:
        tty.setraw(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())
        chan.settimeout(0.0)

        processInitialAutomatedCommands(chan)

        while True:
            r, w, e = select.select([chan, sys.stdin], [], [])
            if chan in r:
                try:
                    x = u(chan.recv(4096))
                    if len(x) == 0:
                        sys.stdout.write("\r\n*** EOF\r\n")
                        break
                    sys.stdout.write(x)

                    processAutomatedEvent(chan,x)

                    sys.stdout.flush()
                except socket.timeout:
                    pass
            if sys.stdin in r:
                x = sys.stdin.read(1)
                if len(x) == 0:
                    break
                chan.send(x)
    except:
        pass

    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)


# thanks to Mike Looijmans for this code
def windows_shell(chan):

    sys.stdout.write(
        "Line-buffered terminal emulation. Press F6 or ^Z to send EOF.\r\n\r\n"
    )

    commander = threading.Thread(target=processGlobalPendingCommands, args=(chan,))
    commander.daemon = True
    commander.start()

    def writeall(sock):
        while True:
            data = sock.recv(4096)
            if not data:
                sys.stdout.write("\r\n*** EOF ***\r\n\r\n")
                sys.stdout.flush()
                break
            sys.stdout.write(str(data))

            processAutomatedEvent(sock,data)

            sys.stdout.flush()

    writer = threading.Thread(target=writeall, args=(chan,))
    writer.start()

    processInitialAutomatedCommands(chan)

    charList=[]

    try:
        while True:
            if writer.is_alive():
                if usingInteractivity:
                    d = sys.stdin.read(1)
                    chan.send(d)

                    #Clean exit control
                    charList.append(str(d).lower().strip())
                    if len(charList) > 5:
                        charList.pop(0)
                    if not d or "".join(charList).startswith("exit") or exitCommandReceived:
                        time.sleep(2)
                        break
                else:
                    time.sleep(1)
            else:
                break


    except EOFError:
        # user hit ^Z or F6
        pass
    except:
        pass