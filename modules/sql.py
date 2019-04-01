import sqlite3, os

class SQLWrapper:
    db = None
    loaded = False

    def __init__(self, debug=False):
        self.debug = debug
        if self.debug:
            global dbg
            import debug_tools as dbg
        self.db = sqlite3.connect(':memory:')
        self.create_tables()

    def add_users(self, user_list):
        # user_list contains tuples of the form (id, user_name, first_name, last_name).
        try:
            return self.db.executemany('INSERT INTO users VALUES (?, ?, ?, ?);', user_list)
        except:
            if self.debug:
                dbg.bp()

    def add_files(self, file_list):
        # file_list contains tuples of the form (id, type, name, url).
        try:
            return self.db.executemany('INSERT INTO files VALUES (?, ?, ?, ?);', file_list)
        except Exception, e:
            print(str(e.__class__) + str(e))
            if self.debug:
                dbg.bp()

    def add_msgs(self, msg_list):
        # message_list contains tuples of the form (ts, uid, type, text, fid).
        try:
            return self.db.executemany('INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?);', msg_list)
        except Exception, e:
            print(str(e.__class__) + str(e))
            if self.debug:
                dbg.bp()

    def ask(self, query, args=None):
        if self.debug: print('Running query: ' + query + '...')
        try:
            if sqlite3.complete_statement(query + ';'):
                if args:
                    cur = self.db.execute(query + ';',args)
                else:
                    cur = self.db.execute(query + ';')
                return cur
            else:
                print('Error: Incomplete Query: ' + query)
        except Exception, e:
            print(str(e.__class__) + str(e))
            if self.debug:
                dbg.bp()

    def build_create(self, table, cols=list(), types=list(), primary=0, keys=list()):
        def get_type(t):
            if t == 'T':
                return 'TEXT'
            elif t == 'I':
                return 'INTEGER'
            elif t == 'R':
                return 'REAL'
            elif t == 'B':
                return 'BLOB'
            elif t == 'N':
                return 'NUMERIC'
            return t
        cols.reverse()
        types.reverse()
        query = "CREATE TABLE " + table + ' ('
        t = get_type(types.pop())
        query += cols.pop() + ' ' + t
        if primary == 1:
            query += ' PRIMARY KEY'
        primary -= 1
        while len(cols) > 0:
            t = get_type(types.pop())
            query += ', ' + cols.pop() + ' ' + t
            if primary == 1:
                query += ' PRIMARY KEY'
            primary -= 1
        while len(keys) > 0:
            key, tab, ref = keys.pop()
            query += ', FOREIGN KEY (' + key + ') REFERENCES ' + tab + '(' + ref + ')'
        query += ')'
        return query

    def build_insert(self, table): pass

    def build_select(self, cols=['*'], tables=['messages'], joins=[], constraints=[], group=[], order=[], join_type='INNER'):
        cols.reverse()
        tables.reverse()
        joins.reverse()
        constraints.reverse()
        group.reverse()
        order.reverse()
        query = "SELECT " + cols.pop()
        while len(cols) > 0:
            query += ", " + cols.pop()
        query += " FROM " + tables.pop()
        while len(tables) > 0:
            query += ' ' + join_type + " JOIN " + tables.pop() + " ON " + joins.pop()
        if len(constraints) > 0:
            query += " WHERE " + constraints.pop()
            while len(constraints) > 0:
                query += " AND " + constraints.pop()
        if len(group) > 0:
            query += " GROUP BY " + group.pop()
            while len(group) > 0:
                query += ", " + group.pop()
        if len(order) > 0:
            query += " ORDER BY " + order.pop()
            while len(order) > 0:
                query += ", " + order.pop()
        return query

    def clear_tables(self):
        del self.db
        self.db = sqlite3.connect(':memory:')
        self.create_tables()

    def create_tables(self):
        msg_tb = self.build_create(table='messages',
            cols=['ts','date','time','uid','mtype','mtext','fid','io'],
            types=['R','T','T','T','T','T','T','I'],
            keys=[('uid','users','uid'),('fid','files','fid')]
            )
        user_tb = self.build_create(table='users',
            cols=['uid','uname','first','last'],
            types=['T','T','T','T'],
            )
        file_tb = self.build_create(table='files',
            cols=['fid','ftype','fname','furl'],
            types=['T','T','T','T'],
            )
        if self.debug:
            tbls = {'Messages':msg_tb,'Users':user_tb,'Files':file_tb}
            dbg.tree(tbls,1,'Creation Queries')
        self.ask(user_tb)
        self.ask(file_tb)
        self.ask(msg_tb)
