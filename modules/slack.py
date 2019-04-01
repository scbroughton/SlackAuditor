import datetime as dt
import math
import time
from slackclient import SlackClient

class SlackWrapper:
    bot_token = None              # OAuth authentication token for this bot.
    channel_id = None             # Maps channel names and channel IDs.
    end = None                    # End of time frame.
    start = None                  # Start of time frame.
    _files = list()               # Tuples of files.
    _msgs = list()                # Tuples of messages.
    _slack = None                 # The Slack bot.
    _threads = list()             # List of threads found.  Each thread is a list
    _users = list()               # Tuples of users.
    _uids = set()                 # Set of user IDs.

    def __init__(self, token, debug=False):
        self.debug = debug
        if self.debug:
            global dbg
            import debug_tools as dbg
        self.token = token
        self._slack = SlackClient(self.token)
        packet = self.call('auth.test')
        self.name = packet['user']
        self.id = packet['user_id']
        self.workspace = packet['team']
        self.workspace_id = packet['team_id']
        if self.debug:
            app = {
                'Proxy Username':self.name,
                'Proxy User ID':self.id,
                'Workspace Name':self.workspace,
                'Workspace ID':self.workspace_id
                }
            dbg.tree(app,1,'App Details')

    def call(self, api, **kwargs):
        try:
            out = self._slack.api_call(api, **kwargs)
            if not out['ok']:
                if 'Retry-After' in response['headers'].keys():
                    # We're being rate-limited for calling too much.
                    delay = response['headers']['Retry-After']
                    if self.debug: print('Rate limited.  Waiting ' + delay + ' seconds.')
                    time.sleep(int(delay))
                    return self.call(api, **kwargs)
                else:
                    # Call succeeded, but API failed. A remote error.
                    print('Error in call to ' + api + ':')
                    print('\tArgs: ' + str(kwargs))
                    print('\tError: ' + out['error'])
                    if self.debug:
                        dbg.tree(out,1,'Returned Message')
                        dbg.bp()
            return out
        except Exception, e:
            # Call failed.  A local error.
            print(str(e.__class__) + str(e))
            if self.debug:
                dbg.tree(out,1,'Returned Message')
                dbg.bp()

    def get_files(self): return self._files

    def get_msgs(self): return self._msgs

    def get_threads(self):
        if self._threads == list():
            self._find_threads()
        return self._threads

    def get_users(self):
        self._users = sorted(self._users,key=lambda u: u[3]+' '+u[2])
        return self._users

    def history(self, cname):
        if cname != self.channel_name:
            if self.update(cname):
                return True
        print('\nGetting history...')
        self._clear_files()
        self._clear_msgs()
        latest = self.end
        packet = self.call('conversations.history',
            channel=self.channel_id,
            oldest=self.start,
            latest=self.end,
            )
        if self.debug:
            print('Calling conversations.history with channel=' + self.channel_id
                + ', start=' + str(self.start) + ', and end=' + str(self.end) + '.')
        if not packet['ok']:
            print(msg['error'])
            if self.debug:
                dbg.bp()
        while packet['has_more']:
            for m in packet['messages']:
                parsed = self._parse_message(m)
                if parsed:
                    self._msgs.append(parsed)
            if self.debug:
                print('---Get Next Page---')
            packet = self.call('conversations.history',
                channel=self.channel_id,
                oldest=self.start,
                latest=self.end,
                cursor=packet['response_metadata']['next_cursor']
                )
        for m in packet['messages']:
            parsed = self._parse_message(m)
            if parsed:
                self._msgs.append(parsed)
        print('\t' + str(len(self._msgs)) + ' messages found.')
        return False

    def timeframe(self, start=None, end=None):
        if start is None and end is None:
            print('\nTime must be in YYYY/MM/DD HH:MM:SS format.')
            print('\tType "q" to quit.')
            print('\tType "-" to go back 3 years from today.')
            start = raw_input('Begin time: ')
            if start == 'q':
                # Quit
                return False
            print('\tType "-" to use current datetime.')
            end = raw_input('End time: ')
        if start == '-':
            # Current retention policy only keeps 3 years of messages.
            # No point in going further back.
            start = (dt.datetime.now() - dt.timedelta(1095)).strftime('%Y/%m/%d %H:%M:%S').split()
        if end == '-':
            end = dt.datetime.now().strftime('%Y/%m/%d %H:%M:%S').split()
        self.start = self._to_ts(start)
        self.end = self._to_ts(end)
        if self.debug: dbg.tree({'start':self.start,'end':self.end},1,'Timeframe')
        return True

    def update(self, name, id=None, users=None):
        self._clear_files()
        self._clear_msgs()
        self._clear_users(users)
        if id is None:
            id = self._find_channel_id(name)
            if id is None:
                return None
        self.channel_name = name
        self.channel_id = id
        return self.channel_id

    def _clear_files(self): self._files = list()

    def _clear_msgs(self): self._msgs = list()

    def _clear_threads(self): self._threads = list()

    def _clear_users(self, users):
        self._uids = set()
        if users is None:
            self._users = list()
        else:
            self._users = users
            for user in users:
                self._uids.add(user[0])

    def _find_channel_id(self, cname):
        self.channel_name = cname
        print('\nGetting channel...')
        info = self.call('conversations.list',
            types='private_channel'
            )
        while info['response_metadata']['next_cursor'] != '':
            # While there are more pages...
            next_cursor = info['response_metadata']['next_cursor']
            channel_list = info['channels']
            for m in xrange(0,len(channel_list)):
                if channel_list[m]['name'] == cname:
                    self.channel_id = channel_list[m]['id']
                    if self.debug:
                        print('\t---Channel found:')
                        print('\t' + cname + ' : ' + self.channel_id)
                    return self.channel_id
            if self.debug: print('---Getting Next Page---')
            info = self.call('conversations.list',
                types='public_channel,private_channel',
                cursor=next_cursor
                )
        channel_list = info['channels']
        for m in xrange(0,len(channel_list)):
            if channel_list[m]['name'] == cname:
                self.channel_id = channel_list[m]['id']
                if self.debug:
                    print('\t---Channel found:')
                    print('\t' + cname + ' : ' + self.channel_id)
                return self.channel_id
        print('\tChannel not found.')
        if self.debug: dbg.bp()
        return None

    def _find_user(self, uid):
        user = self.call('users.info',user=uid)['user']
        try:
            name = user['profile']['display_name_normalized']
        except KeyError:
            name = user['name'].encode('utf-8')
        try:
            real = user['profile']['real_name_normalized']
        except KeyError:
            real = user['real_name'].encode('utf-8')
        index = real.rfind(' ')
        try:
            first, last = real[:index], real[index+1:]
        except:
            dbg.bp()
        return uid, name, first, last

    def _find_users(self, channel):
        print('\nGetting users...')
        info = self.call('conversations.members', channel=self.channel_id)
        while info['response_metadata']['next_cursor'] != '':
            # While there are more pages...
            next_cursor = info['response_metadata']['next_cursor']
            for uid in info['members']:
                user = self._find_user(uid)
                self._users.append(user)
                self._uids.add(user[0])
                if self.debug:
                    try: print('\t' + user[1] + ' : ' + user[2] + ' ' + user[3])
                    except:
                        if self.debug:
                            dbg.bp()
            if self.debug: print('---Get Next Page---')
            info = self.call('conversations.members',
                channel=self.channel_id,
                cursor=next_cursor
                )
        for uid in info['members']:
            if uid not in self._uids:
                user = self._find_user(uid)
                self._users.append(user)
                self._uids.add(user[0])
                try: print('\t' + user[1] + ' : ' + user[2] + ' ' + user[3])
                except:
                    if self.debug:
                        dbg.bp()

    def _find_thread(self, ts):
        thread = list()
        packet = self.call('conversations.replies',
            channel=self.channel_id,
            ts=ts,
            )
        while packet['has_more']:
            for m in packet['messages']:
                parsed = self._parse_message(m)
                if parsed:
                    thread.append(parsed)
                packet = self.call('conversations.replies',
                    channel=self.channel_id,
                    ts=ts,
                    cursor=packet['response_metadata']['next_cursor']
                    )
            return None
        for m in packet['messages']:
            parsed = self._parse_message(m)
            if parsed:
                thread.append(parsed)
        if len(thread) == 1:
            # This is just an ordinary message, not a thread.
            return None
        return sorted(thread,key=lambda m: m[0])
        # Sorts the thread earliest to latest.

    def _find_threads(self):
        for msg in self._msgs:
            thread = self._find_thread(msg[0])
            if thread is not None:
                self._threads.append(thread)

    def _parse_message(self, msg, ignore=[]):
        # ignore is a list of message types that should be ignored.
        ignore = set(ignore)
        date, time = self._to_date(msg['ts'])
        ts = float(msg['ts'])
        mtype = None
        text = None
        fid = None
        try:
            uid = msg['user']
            if uid not in self._uids:
                self._users.append(self._find_user(uid))
                self._uids.add(uid)
        except KeyError:
            # Message is of subtype bot_message, file_comment, message_changed,
            #    message_deleted, or message_replied.
            return None
        try: mtype = msg['subtype']
        except KeyError:
            # Message has no subtype, so it's a regular message.
            mtype = 'message'
        if mtype == 'message':
            if 'message' in ignore: return None
            text = msg['text']
        elif mtype == 'file_share':
            if 'file_share' in ignore: return None
            mtype = 'file'
            fid = msg['file']['id']
            ftype = msg['file']['filetype']
            fname = msg['file']['title']
            try:
                text = msg['file']['initial_comment']['comment']
            except KeyError:
                text = fname
            url = msg['file']['url_private_download']
            self._files.append((fid, ftype, fname, url))
        elif mtype == 'channel_join':
            if 'channel_join' in ignore: return None
            # How to deal with channel_join message should be here.
            # Eventually, all message types should be available with
            #    processing determined by virtual functions to be
            #    implemented by the user.  Eventually.
        else:
            # Message is of type channel/group_archive, _leave, _name, _purpose,
            #    _topic, _unarchive, file_mention, me_message, pinned_item,
            #    thread_broadcast, or unpinned_item.
            # Note that, if the message is from a *.history call, then messages of
            #    subtype message_changed, message_deleted, and message_replied
            #    won't appear.  They have the "hidden" property.
            # Only calls to *.replies methods can find thread replies.
            return None
        return [ts, date, time, uid, mtype, text, fid]

    def _to_date(self, ts):
        # Takes POSIX timestamp and returns local (date,time) tuple of strings
        return dt.datetime.fromtimestamp(float(ts)).strftime('%Y/%m/%d %H:%M:%S:%f').split()

    def _to_ts(self, datetime):
        # Takes local [date,time] list of strings and returns POSIX timestamp.
        if datetime == 'now':
            dtg = dt.datetime.now()
        else:
            d = dt.date(*map(lambda d: int(d),datetime[0].split('/')))
            t = dt.time(*map(lambda t: int(t),datetime[1].split(':')))
            dtg = dt.datetime.combine(d, t)
        return '{0:.6f}'.format(time.mktime(dtg.timetuple()))
