import argparse as ap
import ConfigParser as cp
import datetime as dt
import os
import re

from modules.excel import ExcelWrapper as excel
from modules.slack import SlackWrapper as slack
from modules.sql import SQLWrapper as sql

file_date_re = re.compile('(20\d\d)?.?(\d\d).?(\d\d).?(20\d\d)?.*xlsx')
clock_in_re = re.compile('hi|hello|(log*|sign)ing *on|(log*|sign)ed *on|go*d *morning|gm',re.IGNORECASE)
clock_out_re = re.compile('(good)?bye|(log*|sign)ing *off|(log*|sign)ed *off|thanks|leav.',re.IGNORECASE)
clock_unk_re = re.compile('yesterday|\d\d(:\d\d)? *?(a|p)m|mis*ed|forgot|is*ue',re.IGNORECASE)

def parse_args():
    config = cp.RawConfigParser(defaults={'EXCEL':'out.xlsx','TEMPLATE':'template.xlsx','CHANNEL':'wmhcl'}, allow_no_value=True)
    today = dt.datetime.now()
    yesterday = today-dt.timedelta(1)
    p = ap.ArgumentParser(description='Read messages from a Slack channel and write timestamps to an Excel workbook.')
    p.add_argument('--debug', action='store_true', dest='DEBUG', help='activate debug mode')
    p.add_argument('--version', action='version', version='%(prog)s 0.2')
    p.add_argument('-f', type=str, dest='INIT', default='.\\modules\\init.config', help='get values from the file "INIT" instead of init.config')
    p.s = p.add_argument_group('Slackbot arguments')
    p.s.add_argument('-c', type=str, dest='CHANNEL', help='read the "CHANNEL" Slack channel instead of wmhcl')
    p.s.add_argument('-s', nargs=2, type=str, dest='START', metavar=('YYYY/MM/DD','HH:MM:SS'),
        default=[yesterday.strftime('%Y/%m/%d'),yesterday.strftime('%H:%M:%S')],
        help='read all Slack messages that were written after "YYYY/MM/DD HH:MM:SS"')
    p.s.add_argument('-e', nargs=2, type=str, dest='END', metavar=('YYYY/MM/DD','HH:MM:SS'),
        default=[today.strftime('%Y/%m/%d'),today.strftime('%H:%M:%S')],
        help='read all Slack messages that were written before "YYYY/MM/DD HH:MM:SS"')
    p.s.add_argument('-T', type=str, dest='APITOKEN', help='use "APITOKEN" to authenticate with the Slack servers')
    p.x = p.add_argument_group('Excel arguments')
    p.x.add_argument('-x', type=str, dest='EXCEL', help='write the Excel output to the file "EXCEL"')
    p.x.add_argument('-t', type=str, dest='TEMPLATE', help='use the Excel file "TEMPLATE" as a template for the report')
    a = vars(p.parse_args())
    config.read(a['INIT'])
    for key in a.keys():
        if a[key] is None:
            not_found = True
            for section in ['Auditor','Slack','SQLite','Excel']:
                try:    # If key is in the current section, set a[key] to its value.  If not, try looking in the next section.
                    a[key] = config.get(section,key)
                    not_found = False
                    break
                except cp.NoOptionError:
                    continue
            if not_found: raise SystemExit('Required parameter unspecified: ' + key)
    if a['DEBUG'] == 'true' or a['DEBUG'] == True:
        a['DEBUG'] = True
    else:
        a['DEBUG'] = False
    if config.has_option('Slack','CHANNEL') and a['CHANNEL'] == config.get('Slack','CHANNEL'):
        a['CHANNEL_ID'] = config.get('Slack','CHANNEL_ID')
    else:
        a['CHANNEL'] = None
        a['CHANNEL_ID'] = None
    return a

def write_config(arg, cid):
    config = cp.RawConfigParser()
    config.add_section('Auditor')
    config.add_section('Slack')
    config.add_section('SQLite')
    config.add_section('Excel')
    config.set('Auditor','DEBUG',arg['DEBUG'])
    config.set('Slack','APITOKEN',arg['APITOKEN'])
    config.set('Slack','CHANNEL',arg['CHANNEL'])
    config.set('Slack','CHANNEL_ID',cid)
    config.set('Excel','OUTPUT',arg['EXCEL'])
    config.set('Excel','TEMPLATE',arg['TEMPLATE'])
    with open(arg['INIT'], 'w') as f:
        config.write(f)

def analyze(msg):
    # ts, date, time, userID, message_type, message_text, fileID
    io = 0   # 1 = clock in, -1 = clock out, 0 = unknown.

    ts = float(msg[0])
    day = msg[1].split('/')[2]
    hour = int(msg[2].split(':')[0])
    text = msg[5]
    file = msg[6]

    refile = file_date_re.search(text)
    rein = clock_in_re.search(text)
    reout = clock_out_re.search(text)
    reunk = clock_unk_re.search(text)

    if refile:
        if refile.group(1) == '2018':   # YYYY.MM.DD format
            if refile.group(3) == day:
                io = -1
        elif refile.group(2) == day:   # MM.DD.YYYY or MM.DD formats
            io = -1
    elif reout:
        io = -1
    elif rein:
        io = 1
        if hour > 17:
            msg[1] = (dt.datetime.fromtimestamp(ts)+dt.timedelta(1)).date().strftime('%Y/%m/%d')
    if reunk:
        io = 0
    msg.append(io)
    return tuple(msg)

# Parse the command line
arg = parse_args()
os.system('cls')

# Load packages for debugging
if arg['DEBUG']:
    import debug_tools as dbg
    dbg.tree(arg,1,'Command Line Arguments')
# Initialize the instances.
print('\nConnecting...')
listener = slack(token=arg['APITOKEN'], debug=arg['DEBUG'])
scriber  = sql(debug=arg['DEBUG'])
reporter = excel(template=arg['TEMPLATE'], debug=arg['DEBUG'])
print('\nConnected.')
cid = listener.update(arg['CHANNEL'], arg['CHANNEL_ID'])

# Set the timeframe to be documented.
print('\nGetting timeframe...')
alive = listener.timeframe(arg['START'], arg['END'])
print('\tFrom ' + repr(listener._to_date(listener.start)) + ' (ts=' + listener.start \
    + ') to ' + repr(listener._to_date(listener.end)) + ' (ts=' + listener.end + ')')

while alive:
    messages = list()
    if listener.history(arg['CHANNEL']):
        print('An Error occurred while getting the historical data')
        if arg['DEBUG']: dbg.bp()
    arg['USERS'] = listener.get_users()
    print('\nAdding Users...')
    cur = scriber.add_users(listener.get_users())
    print('\t' + str(cur.rowcount+1) + ' users added.')
    print('\nAdding Files...')
    cur = scriber.add_files(listener.get_files())
    print('\t' + str(cur.rowcount+1) + ' files added.')
    print('\nAdding Messages...')
    for msg in listener.get_msgs():
        messages.append(analyze(msg))
    cur = scriber.add_msgs(messages)
    print('\t' + str(cur.rowcount+1) + ' messages added.')
    if arg['DEBUG']:
        q = scriber.build_select(
            cols=['m.date','m.time','u.uname','u.first','u.last','m.io','m.mtype',
                'm.mtext','f.fname','f.ftype'],
            tables=['messages m','users u','files f'],
            join_type='LEFT',
            joins=['m.uid = u.uid','m.fid = f.fid'])
        cur = scriber.ask(q)
        dbg.table(cur,'ALL_TABLES')
    q = scriber.build_select(
        cols=['CASE WHEN a.fid != NULL THEN a.ts ELSE b.ts END'],
        tables=['messages a','messages b'],
        joins=['a.uid = b.uid'],
        constraints=['a.ts < b.ts', 'b.ts < a.ts + 600'])
    q = scriber.build_select(constraints=['ts NOT IN (' + q + ')'])
    q = scriber.build_select(
        cols=['u.last','u.first','m.date','m.time','m.mtext','m.ts', 'm.fid','m.io'],
        tables=['(' + q + ') m','users u'],
        joins=['m.uid = u.uid'],
        order=['u.last DESC', 'u.first DESC','m.date DESC', 'm.time DESC'])
    q = scriber.build_select(
        cols=['m.last','m.first','m.date','m.time','m.mtext','m.ts','m.io'],
        tables=['(' + q + ') m','files f'],
        joins=['m.fid = f.fid'],
        join_type='LEFT',
        order=['m.date','m.last','m.first','m.ts']
        )
    messages = scriber.ask(q).fetchall()
    reporter.fill(messages)
    print('\nSaving Excel...')
    reporter.save(arg['EXCEL'])
    print('\nClearing tables...')
    scriber.clear_tables()
    alive = False
    choice = raw_input('\nChange the channel (Y/N)?    ')
    if choice == 'Y' or choice == 'y':
        alive = True
        choice = raw_input('\tNew channel : ')
        arg['CHANNEL'] = choice
        listener.update(choice)
    choice = raw_input('\nChange the timeframe (Y/N)?    ')
    if choice == 'Y' or choice == 'y':
        alive = listener.timeframe()

choice = raw_input('\nWrite changes to init.config (Y/N)?    ')
if choice == 'Y' or choice == 'y':
    write_config(arg, cid)