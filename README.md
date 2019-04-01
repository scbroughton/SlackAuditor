# SlackAuditor
A Python script to log messages on Slack using Slack's bot API.

This script was created in order to automate a specific report at work, so it's very focused and doesn't have many options for extensibility.  As the report is no longer being generated and nothing similar is being requested at the moment, it's unlikely that I'll refactor this code to make it more general.

## Getting Started
* Clone this repository into a directory.
* The program requires an input Excel file that will act as a template for the results.
* Any layout and formatting information in the template will be retained in the final output.
* On the first run, you will also need to specify your bot's API token.
* After the program runs, you'll be prompted to save your settings into a config file to simplify future runs of the program.

### Prerequisites
* [Python 2](https://www.python.org/downloads/)
* [Pip](https://pypi.org/project/pip/)
* [SlackClient](https://pypi.org/project/slackclient/)
* [OpenPyXL](https://pypi.org/project/openpyxl/)

### Usage
    slack_audit.py [-h] [--debug] [--version] [-f INITFILE] [-c CHANNNEL]
                   [-s YYYY/MM/DD HH:MM:SS] [-e YYYY/MM/DD HH:MM:SS]
                   [-T APITOKEN] [-x OUTPUTFILE] [-t TEMPLATEFILE]
    
    optional arguments:
      -h, --help               show this help message and exit.
      --debug                  activate debug mode.
      --version                show program's version number and exit.
      -f INITFILE              get values from INITFILE instead of init.config.

    required arguments:
      -c CHANNEL               read this Slack channel.
      -s YYYY/MM/DD HH:MM:SS   read all Slack messages that were written after this time.
      -e YYYY/MM/DD HH:MM:SS   read all Slack messages that were written before this time.
      -T APITOKEN              use APITOKEN to authenticate with the Slack servers.
      -x OUTPUTFILE            use OUTPUTFILE as the name of the output Excel workbook.
      -t TEMPLATEFILE          use TEMPLATEFILE as a base for the output workbook.

If init.config is in the modules folder or the `-f INITFILE` argument is given, parameters defined in those files will be used as defaults, though any command-line arguments will override them.  When run without a start date/time argument, the default start time is 24 hours ago.  When run without an end date/time argument, the default end time is the current time.
