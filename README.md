[![LGPL License](https://img.shields.io/badge/license-LGPL-blue.svg)](https://github.com/paramiko/paramiko/blob/main/LICENSE)
# Automated SSH

Automated SSH is a solution written in python to allow automation of interactive operations made through a console ssh connection.

This tool can be used in DevOps CI/CD pipelines which require console interactive operations and take out the human intervention. It is also useful if you want to build some functional tests against text based programs.


Basic parameters:
| Parameter | Type     | Description                |
| :-------- | :------- | :------------------------- |
| `user@host` | `string` | **Required**. The ssh user and the ssh remote server |
| `password ⚡️ ` | `string` | **Optional**. Plain text ssh password. USE ENVIRONMENT VARIABLES for this. Passing the password as command line parameter should only be done in masked pipelines and It is risky. Use It under your own responsibility.|
| `pk` | `string` | **Optional**. Private key file location. |
| `port` | `int` | **Optional**. SSH Server listening port. Default is 22. |


Automation parameters:
| Parameter | Type     | Description                |
| :-------- | :------- | :------------------------- |
| ` config-file` | `string` | **Required for automation**. Location of the yaml file with the declarative automation configuration. |
| `map` | `string` | **Required if using variables**. Defines the values for the variables used inside the config-file. |


## Examples:

#### - Start a console connection (NOT Automated). This way, the program will run a bit like the tratiditional unix ssh command.

```
  python automated_ssh.py my_ssh_user@some_ssh_server
```
```
  python automated_ssh.py my_ssh_user@some_ssh_server pk=my_openssh_private_key_file
```

#### - Start a console connection with automation parameters. This way, the program will run sending keystrokes and commands depending on what it detects on the "virtual screen", based on what is specified in the yaml configuration file.

```
  python automated_ssh.py my_ssh_user@some_ssh_server config-file=automated_ssh_config.yaml
```


#### - Similarly to the previous example we are starting an automated process but in addition we are passing variables values that will be expanded while executing the commands in the configuration file. The variable names in the configuration file MUST be enclosed in double curly braces like this: {{myVar}}

```
  python automated_ssh.py my_ssh_user@some_ssh_server config-file=automated_ssh_config.yaml map=myVar:myValue map=myVar2:myValue2
```


## Configuration file:

The configuration is set in a text file in YAML format. The main sections in the file are:

#### - Commands or keystrokes to send once the connection is started:

This section is configured using the initialCommands list. This list defines which characters that will be queued for transmission once the ssh connection is established. In other words: execute which commands or send which key strokes when the connection is established. Example:

```
initialCommands:
  - "ls \n"
  - "my_console_program_start_command \n"

```

#### - Commands or keystrokes to send when some expected text y detected on the "virtual screen":

This section is configured using the expectedTextsDictionary dictionary. This dictionary holds character sequences (expected texts) which enclose a list of characters will be queued for transmission once the "expected text" is identified in the incoming ssh stream. In other words: execute which commands or send which key strokes when an incoming specific text is detected. Example:

```
expectedTextsDictionary:
    
  "Not enaugh disk space.": 
    - "quit \n"
    - "rm /temp/*.log \n"
    - "my_console_program_start_command \n"

  "1 task is pending": 
    - "process task 1 \n"

  "No more pending tasks": 
    - "quit \n"
    - "exit \n"
```


#### - Commands or keystrokes that can be reused

This section is configured using the expectedTextListAdditions dictionary. This dictionary holds pre existent expectedTextsDictionary entries which enclose a list of "custom commands lists" which has to be appended to the expectedTextsDictionary entry list of commands. In other words: Allows adding new commands or key strokes to a predefined expected text list definition. This helps for reusing commands lists between different expected texts. Example:

```
reusableCommandListExample:
  - "git\n"
  - "exit\n"

expectedTextsDictionary:
  "Last login": 
    - "ls\n"

expectedTextListAdditions:
  "Last login":
    - reusableCommandListExample

```

In the example, reusableCommandListExample is a custom list which enclosed commands will be queued for transmission after the specific commands for the expected text "Last login" are executed.


## Automated_SSH control instructions

These are instructions that make special operations on the behavior of the automated process
and are treated as if they were commands to be sent but they are not sent really.

They are defined this way: _as_control=<_as_control command>:<_as_control command parameter data>
Example: 

```
expectedTextsDictionary:
  "Last login": 
    - "ls\n"
	- _as_control=set-between-new-command-seconds:3
```

List of available as control commands:

- set-between-new-command-seconds : Wait the defined seconds before sending each queued line of
  characters (command) to the ssh server. This time is set globally for all the queued commands.
  
  Example:
    _as_control=set-between-new-command-seconds:3

- set-exit-code : Sets the exit code that will be reported by the program to the shell when it finishes.
  The new exit code will be set only if it is greater than the actual one or if it is lower than zero.
  
  Example:
    _as_control=set-exit-code:3

  If the exit code ends being lower than zero, the reported exit code will be 1.

  This behavior should match the gravity of the error found. The grater the gravity of the error found,
  the grater the value of the exit code.

- remove_expected_text: removes an entry in the expectedTextsDictionary. This should be made to avoid
  unwanted loops once an expected text is found and it should be processed no more times.
  
  Example:
    _as_control=remove_expected_text:user

    This works if there is a "user" expected text defined like this:
         expectedTextsDictionary:

           "user":
             - "pablo\n"


- execute_expected_text_commands : executes the commands list of the specified expected text as if it was 
  detected in the incoming stream; but a condition must be met
  
  Example:
    _as_control=execute_expected_text_commands:Last login_condition_int(localDataDict['exit-code']) < 0

    Explanation:
      - "Last login" is the configured expected text
      - "_condition_" is always there to separate the expected text and the condition 
      - "int(localDataDict['exit-code']) < 0" is the True/False python code condition that will be evaluated
 

- clear-commands-queue : clears the actual commands queue to be sent, erasing ALL previous queued commands.
  Please note that although it does not require parameters, the two points at the end are required.
  
  Example:
    _as_control=clear-commands-queue:


## Runtimes and compilation information


Automated_ssh was tested with python versions 2.7 and 3.10 installed on Linux and Windows but the behavior of the program will change if It is run using Windows.

Running the program on Linux, It will not have any issues. Running the program on Windows there are some limitations:

- If It is run using python 3, the characters in the terminal will show garbage even if you are using fancy terminal programs like Hyper (https://hyper.is/)
- When running an automated process, the manual interactivity is completely disabled. If the exit command is not sent in the automation, the only way to finish the process is using CTRL+C

The compiled binary for Windows was generated using pyinstaller and because the previous reasons, the python version used for the compilation was 2.7
