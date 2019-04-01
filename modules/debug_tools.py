from pdb import set_trace

types = {"<type 'dict'>":'dic', "<type 'NoneType'>":'Nul', "<type 'list'>":'lst',
        "<type 'int'>":'int', "<type 'bool'>":'bol', "<type 'unicode'>":'uni',
        "<type 'str'>":'str', "<type 'tuple'>":'tup',"<type 'float'>":'dbl',
        "<type 'int'>":'int', "<type 'set'>":'set'}

def tree(data, tree=0, name='ROOT NODE'):
    if   tree == 0: tree = full_tree(data, name, '')
    elif tree == 1: tree = value_tree(data, name, '')
    elif tree == 2: tree = type_tree(data, name, '')
    else: tree = 'Error: No tree type'
    print('\n' + tree + '\n')

def full_tree(data, name='ROOT NODE', level=''):
    global types
    t = types[str(type(data))]
    s = level + name + ' <' + t + '> = '
    if t == 'dic':
        s += '{\n'
        for attr in data:
            s += value_tree(data[attr],str(attr),level+'    ') + '\n'
        s += level+'    }\n'
    elif t == 'lst':
        print(s + '[')
        for i in range(0, len(data)):
            s += value_tree(data[i],'Entry '+str(i),level+'    ') + '\n'
        s += level + '    ]\n'
    elif t == 'tup':
        s += '(\n'
        for i in range(0, len(data)):
            s += value_tree(data[i],'','') + ', '
        s += level + '    )\n'
    elif t == 'uni':
        s += '"' + str(data.encode('ascii','ignore')) + '"'
    else:
        s += str(data)
    return s

def type_tree(data, name='ROOT NODE', level=''):
    global types
    t = types[str(type(data))]
    if name == '':
        s = level + '<' + t + '>'
    else:
        s = level + name + ' : <' + t + '>'
    if t == 'dic':
        s += ' {\n'
        for attr in data:
            s += type_tree(data[attr],str(attr),level+'    ') + '\n'
        s += level + '    }\n'
    elif t == 'lst':
        s += ' [\n'
        for i in range(0, len(data)):
            s += type_tree(data[i],'',level+'    ') + '\n'
        s += level + '    ]\n'
    elif t == 'tup':
        s += ' ('
        for i in range(0, len(data)):
            s += '<' + t + '>, '
        s = s[:-2] + ')\n'
    return s

def value_tree(data, name='ROOT NODE', level=''):
    global types
    t = types[str(type(data))]
    if name == '':
        s = level
    else:
        s = level + name + ' : '
    if t == 'dic':
        s += '{\n'
        for attr in data:
            s += value_tree(data[attr],str(attr),level+'    ') + '\n'
        s += level + '    }\n'
    elif t == 'lst':
        s += '[\n'
        for i in range(0, len(data)):
            s += value_tree(data[i],'',level+'    ') + '\n'
        s += level + '    ]\n'
    elif t == 'tup':
        s += ' ('
        for i in range(0, len(data)):
            s += value_tree(data[i],'','') + ', '
        s = s[:-2] + ')'
    elif t == 'uni':
        s += '"' + str(data.encode('ascii','ignore')) + '"'
    else:
        s += str(data)
    return s

def table(cur, name='New Table'):
    print('')
    cols = []
    num_cols = 0
    for col in cur.description:
        cols.append(col[0])
        num_cols += 1
    rows = cur.fetchall()
    max_len = [len(x) for x in cols]
    for row in rows:
        row = [row] if type(row) not in (list, tuple) else row
        for index, col in enumerate(row):
            if max_len[index] < len(str(col)):
                max_len[index] = len(str(col))
    output = '-' * (sum(max_len) + num_cols + 1) + '\n'
    output += '|' + ''.join([h + ' ' * (l - len(h)) + '|' for h, l in zip(cols, max_len)]) + '\n'
    output += '-' * (sum(max_len) + num_cols + 1) + '\n'
    for row in rows:
        row = [row] if type(row) not in (list, tuple) else row
        output += '|' + ''.join([str(c) + ' ' * (l - len(str(c))) + '|' for c, l in zip(row, max_len)]) + '\n'
    output += '-' * (sum(max_len) + num_cols + 1) + '\n'
    print(output)
    print('')

def bp(): set_trace()  # Set a breakpoint