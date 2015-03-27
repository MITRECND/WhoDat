#!/usr/bin/env python
import re
from ply.lex import TOKEN
import json
import datetime

tokens = [
    'COLON', 
    'WORD', 
    'QUOTED', 
    'OR', 
    'AND', 
    'LPAREN', 
    'RPAREN',
    'FUZZY',
    'REGEX',
    'WILDCARD',
    'DATE'
]

regex_pattern = r'(r"(\\.|[^\t\n\r\f\v"])+")|' + r"(r'(\\.|[^\t\n\r\f\v'])+')"
wildcard_pattern = r'(w"([^\t\n\r\f\v"])+")|' + r"(w'([^\t\n\r\f\v'])+')"

# Tokens
# Regex precendence is functions in file order followed by regex string with decreasing complexity
t_QUOTED =  r'"(\\[\\"~:\(\)]|[^\t\n\r\f\v\\"~:\(\)])+"|' + r"'(\\[\\~':\(\)]|[^\t\n\r\f\v\\'~:\(\)])*'"
t_WORD =    r'((\\[\\~:\(\)])|[^\s\\~:\(\)\'"])+'
t_DATE =    r'[0-9]{4}-((0[1-9])|1[1-2])-((0[1-9])|([1-2][0-9])|(3[0-1]))'
t_FUZZY =   r'~[0-9]?'
t_COLON =   r':'
t_LPAREN =  r'\('
t_RPAREN =  r'\)'


@TOKEN(regex_pattern)
def t_REGEX(t):
    return t;

@TOKEN(wildcard_pattern)
def t_WILDCARD(t):
    #Need to check manually since otherwise the token won't match properly
    if ' ' in t.value:
        t_error(t)
        return None
    return t;

@TOKEN('OR')
def t_OR(t):
    return t

@TOKEN('AND')
def t_AND(t):
    return t

t_ignore = " \t\n"

#def t_newline(t):
#    r'\n+'
#    t.lexer.lineno += t.value.count("\n")

def t_error(t):
    raise ValueError("Illegal sequence: %s" % t.value)
    #t.lexer.skip(1)

# Build the lexer
import ply.lex as lex
lex.lex()

precedence = (
        ('left', 'QUOTED'),
        ('right', 'AND', 'OR'),
        ('left', 'COLON'),
        ('left', 'WORD'),
    )


# Extremely naive method of determining if they're searching
# for a domain or email
def looks_like(term):
    if '@' in term:
        return 'email'
    elif '.' in term:
        return 'domain'

    return None

"""
Grammar

query : (query)
      | query query
      | query AND query
      | query OR query
      | specific
      | daterange
      | terms

specific : FUZZY WORD COLON value
         | WORD COLON value

daterange : WORD COLON DATE
          | WORD COLON DATE COLON DATE
          | WORD COLON COLON DATE
          | WORD COLON DATE COLON

value : string

terms : terms terms
      | string

string : QUOTED
       | WORD
       | REGEX
       | WILDCARD

"""

class String(object):
    def __init__(self, src, type):
        self.string = src
        self.type = type

    def __str__(self):
        return self.string

    def __repr__(self):
        return self.string
    

no_parts = [ 
            'details.registrant_fax',
            'details.registrant_faxExt',   
            'details.registrant_telephone',
            'details.registrant_telephoneExt',
            'details.administrativeContact_fax',
            'details.administrativeContact_faxExt',
            'details.administrativeContact_telephone',
            'details.administrativeContact_telephoneExt',
            ]

date_keywords = {
                    'created': 'details.standardRegCreatedDate',
                    'updated': 'details.standardRegUpdatedDate',
                    'expires': 'details.standardRegExpiresDate'
                }

original_keywords = [
                        'domainName', 
                        'administrativeContact_email', 
                        'administrativeContact_name',
                        'administrativeContact_organization',
                        'administrativeContact_street1',
                        'administrativeContact_street2',
                        'administrativeContact_street3',
                        'administrativeContact_street4',
                        'administrativeContact_city',
                        'administrativeContact_state',
                        'administrativeContact_postalCode',
                        'administrativeContact_country',
                        'administrativeContact_fax',
                        'administrativeContact_faxExt',
                        'administrativeContact_telephone',
                        'administrativeContact_telephoneExt',
                        'registrant_email',
                        'registrant_name',
                        'registrant_organization',
                        'registrant_street1',
                        'registrant_street2',
                        'registrant_street3',
                        'registrant_street4',
                        'registrant_city',
                        'registrant_state',
                        'registrant_postalCode',
                        'registrant_country',
                        'registrant_fax',
                        'registrant_faxExt',   
                        'registrant_telephone',
                        'registrant_telephoneExt',
                        'nameServers',
                        'registrarName',
                        'whoisServer'
                    ]

special_keywords = {
                'email_local': [ 
                           "details.administrativeContact_email.local", 
                           "details.registrant_email.local", 
                         ],
                'email_domain': [ 
                           "details.administrativeContact_email.domain", 
                           "details.registrant_email.domain", 
                         ],
                   }

shortcut_keywords = {
                'administrativeContact_street': [
                           'details.administrativeContact_street1',
                           'details.administrativeContact_street2',
                           'details.administrativeContact_street3',
                           'details.administrativeContact_street4',
                            ],
                'registrant_street': [ 
                           'details.registrant_street1',
                           'details.registrant_street2',
                           'details.registrant_street3',
                           'details.registrant_street4',
                            ],
                'dn': ["domainName"],
                'email': [ "details.administrativeContact_email", 
                           "details.registrant_email", 
                         ],
                'name': ['details.administrativeContact_name',
                         'details.registrant_name'
                        ],
                'organization': ['details.administrativeContact_organization',
                                 'details.registrant_organization'
                                ],
                'street': ['details.registrant_street1',
                           'details.registrant_street2',
                           'details.registrant_street3',
                           'details.registrant_street4',
                           'details.administrativeContact_street1',
                           'details.administrativeContact_street2',
                           'details.administrativeContact_street3',
                           'details.administrativeContact_street4',
                          ],
                'city': ['details.administrativeContact_city',
                         'details.registrant_city'
                        ],
                'state': ['details.administrativeContact_state',
                         'details.registrant_state'
                        ],
                'postalCode': ['details.administrativeContact_postalCode',
                               'details.registrant_postalCode'
                              ],
                'country': ['details.administrativeContact_country',
                            'details.registrant_country'
                           ],
                'telephone': ['details.administrativeContact_telephone',
                              'details.registrant_telephone'
                             ],
                'telephoneExt': ['details.administrativeContact_telephoneExt',
                              'details.registrant_telephoneExt'
                             ],
                'fax': ['details.administrativeContact_fax',
                        'details.registrant_fax'
                       ],
                'faxExt': ['details.administrativeContact_faxExt',
                        'details.registrant_faxExt'
                       ],
                'ns': ['details.nameServers'],
                'registrar': ['details.registrarName'],
            }


def p_query_group(t):
    'query : LPAREN query RPAREN'
    t[0] = t[2]

def p_query_query(t):
    '''query : query query
             | query AND query'''

    if len(t) == 4:
        queries = (t[1], t[3])
    else:
        queries = (t[1], t[2])
    print('AND QUERY', queries[0], queries[1])

    query = { "bool": { "must": [] }}
    filt = {'and': []}

    for q in queries:
        qq = q['query']['filtered']['query']
        if 'match_all' not in qq:
            query["bool"]["must"].append(qq)
        qf = q['query']['filtered']['filter']
        if 'match_all' not in qf:
            filt['and'].append(qf)

    if len(filt['and']) == 0:
        filt = {'match_all': {}}
    elif len(filt['and']) == 1:
        filt = filt['and'][0]

    if len(query['bool']['must']) == 0:
        query = {'match_all': {}}
    elif len(query['bool']['must']) == 1:
        query = query['bool']['must'][0]
    

    t[0] = {
        "query": {
            "filtered": {
                "query": query,
                "filter": filt
            }
        }
    }

def p_query_or_query(t):
    'query : query OR query'
    print('OR QUERY', t[1], t[2], t[3])

    query = {"bool": {"should": []}}
    filt = {"or": []}

    for q in (t[1], t[3]):
        qq = q['query']['filtered']['query']
        if 'match_all' not in qq:
            query["bool"]["should"].append(qq)

        qf = q['query']['filtered']['filter']
        if 'match_all' not in qf:
            filt['or'].append(qf)

    if len(filt['or']) == 0:
        filt = {'match_all': {}}
    elif len(filt['or']) == 1:
        filt = filt['or'][0]

    if len(query['bool']['should']) == 0:
        query = {'match_all': {}}
    elif len(query['bool']['should']) == 1:
        query = query['bool']['should'][0]


    t[0] = {
        "query": {
            "filtered": {
                "query": query,
                "filter": filt
            }
        }
    }



def p_query_specific(t):
    'query : specific'
    t[0] = t[1]

def p_query_daterange(t):
    'query : daterange'
    t[0] = t[1]

def p_query_term(t):
    'query : terms'
    print('QString', t[1])
    parts = []

    for st in t[1]:
        ll = looks_like(str(st))
        if ll is None:
            if st.type == 'word':
                parts.append({'match': {'_all': str(st)}})
            else:
                parts.append({'match_phrase': {'_all': str(st)}})
        else:
            if ll == 'email':
                fields = [ "details.administrativeContact_email.parts^2", 
                           "details.registrant_email.parts^2", 
                           "_all" ] 
            elif ll == 'domain':
                fields = [ "domainName.parts^3",
                           "details.administrativeContact_email.parts^2", 
                           "details.registrant_email.parts^2", 
                           "_all"]

            if st.type == 'word':
                parts.append({
                    "multi_match": {
                        "query": str(st),
                        "fields": fields
                    }
                })
            else:
                parts.append({
                    "multi_match": {
                        "query": str(st),
                        "fields": fields,
                        "type" : "phrase"
                    }
                })

        if len(parts) == 1:
            t[0] = {"query": {"filtered": {"query": parts[0], "filter": {"match_all":{}}}}}
        else:
            t[0] = {"query": {"filtered": {"query": {"bool": {"must" : parts }}, "filter": {'match_all': {}}}}}

def p_daterange(t):
    '''daterange : WORD COLON DATE
                 | WORD COLON DATE COLON DATE'''

    if len(t) == 4:
        try:
            start_date = datetime.datetime.strptime(t[3], '%Y-%m-%d')
        except Exception as e:
           print "Invalid Date Format: %s" % str(e) 

        end_date = start_date + datetime.timedelta(1,0)
        key = t[1]
    else:
        try:
            start_date = datetime.datetime.strptime(t[3], '%Y-%m-%d')
            end_date = datetime.datetime.strptime(t[5], '%Y-%m-%d') + datetime.timedelta(1,0)
        except Exception as e:
            print "Invalid Date Range"

        if end_date < start_date:
            print "End date less than start date"
        key = t[1] 

    print start_date, end_date

    if key not in date_keywords:
        raise KeyError("Unknown Key")

    key = date_keywords[key]

    qf = {
    'query':{
        'filtered': {
            'filter': { 
                'range': {
                    key: {
                        'gte': start_date.strftime('%Y-%m-%d %H:%M:%S'),
                        'lt': end_date.strftime('%Y-%m-%d %H:%M:%S'),
                    }
                }
            },
            'query': {'match_all': {}},
            }
        }
    }

    t[0] = qf 

def p_specific(t):
    '''specific : FUZZY WORD COLON value
                | WORD COLON value'''


    """
        Specific searches behave differently depending on what type of
        value type is used and if FUZZY is defined. if value is a:
    
        word -- a general match query will be used on .parts
             -- FUZZY honored
        quoted -> FUZZY is none
                    -- a terms query will be used on the entire string (boost 1.5)
                    -- a terms query will be used on the string split on whitespace against .parts (no boost)
               -> FUZZY is not none
                    -- a match phrase query will be used on the entire string against .parts
        wildcard -- a wildcard query will be used on the entire string (boost 1.5)
                 -- a wildcard query will be used on .parts
                 -- FUZZY ignored
        regex -- a regex query will be used ont he entire string (boost 1.5)
              -- a regex query will be used on .parts
              -- FUZZY ignored
    """
    
    if len(t) == 5:
        if len(t[1]) == 1:
            fuzzy = 'AUTO'
        else:
            fuzzy = int(t[1][1])
        key = t[2]
        value = t[4]
    else:
        key = t[1]
        value = t[3]
        fuzzy = None


    fields1 = []
    fields2 = []

    if key in special_keywords:
        fields1 = special_keywords[key]
        if ((value.type == 'quoted' and 
            fuzzy is None) or value.type == 'regex' or
            value.type == 'wildcard'): 
            for f in fields1:
                if f not in no_parts:
                    f += ".parts"
                    fields2.append(f)
    else:
        if key in shortcut_keywords:
            fields1 = shortcut_keywords[key]
        elif key in original_keywords:
            if key != 'domainName':
                key = 'details.' + key
            fields1 = [key]

        if (value.type == 'word'):
            nf = []
            for f in fields1:
                if f not in no_parts:
                    f += ".parts" 
                nf.append(f)
            fields1 = nf
        elif (value.type == 'quoted' and 
                fuzzy is not None):
            nf = []
            for f in fields1:
                if f not in no_parts:
                    f += ".parts"
                nf.append(f)
            fields1 = nf
        elif ((value.type == 'quoted' and 
                fuzzy is None) or
                value.type == 'wildcard' or
                value.type == 'regex'):
            for f in fields1:
                if f not in no_parts:
                    f += ".parts"
                    fields2.append(f)

    print fields1, fields2

    q = {}

    if value.type == 'word':
        q['multi_match'] = {
            "query": str(value),
            "fields": fields1 
        } 
        if fuzzy is not None:
            q['multi_match']['fuzziness'] = fuzzy

    elif value.type == 'wildcard':
        shds = []
        for f in fields1:
            shd = {'wildcard': {f: {"value": str(value), "boost": 1.5}}}
            shds.append(shd)
        for f in fields2:
            shd = {'wildcard': {f: str(value)}}
            shds.append(shd)
        if len(shds) == 1:
            q['query'] =  shds[0]
        else:
            q['bool'] = {'should': shds}

    elif value.type == 'regex':
        shds = []
        for f in fields1:
            shd = {'regexp': {f: {"value": str(value), "boost": 1.5}}}
            shds.append(shd)
        for f in fields2:
            shd = {'regexp': {f: {"value": str(value)}}}
            shds.append(shd)
        if len(shds) == 1:
            q['query'] = shds[0]
        else:
            q['bool'] = {'should': shds}
    elif value.type == 'quoted':
        if fuzzy is None:
            shds = []
            for f in fields1:
                shd = {'term': { f: {"value": str(value), "boost" : 1.5}}}
                shds.append(shd)
            for f in fields2:
                for p in str(value).split():
                    shd = {'term': {f: p}}
                    shds.append(shd)
            if len(shds) == 1:
                q['query'] = shds[0]
            else:
                q['bool'] = {'should': shds}
        else:
            q['multi_match'] = {
                "query": str(value),
                "fields": fields1,
                "fuzziness": fuzzy
            }

    if 'query' not in q:
        t[0] = {'query': {'filtered': {'filter': {'match_all': {}}, 'query': q}}}
    else:  
        t[0] = {'query': {'filtered': {'filter': {'match_all': {}}, 'query': q['query']}}}

def p_value(t):
    'value : string'
    print("Value", t[1])
    t[0] = t[1]

def p_term(t):
    'terms : string'
    print('Terms', t[1])
    t[0] = [t[1]]

def p_terms(t):
    'terms : terms terms'
    print('Terms', t[1])
    t[0] = []
    t[0].extend(t[1])
    t[0].extend(t[2])


def remove_escapes(t):
    unescaped_string = ""
    parts = re.split(r'(\\.)', t)
    print parts
    for p in parts:
        if p == '':
            continue
        else:
            if p[0] == '\\':
                unescaped_string += p[1]
            else:
                unescaped_string += p 
    return unescaped_string

def p_string_quoted(t):
    'string : QUOTED'
    print("SQuoted", t[1])
    unes = remove_escapes(t[1][1:-1])
    s = String(unes.lower(), 'quoted')
    t[0] = s

def p_string_word(t):
    'string : WORD'
    print("SWord", t[1])
    unes = remove_escapes(t[1])
    w = String(unes.lower(), 'word')
    t[0] = w

def p_string_regex(t):
    'string : REGEX'
    print("SRegex", t[1])
    r = String(t[1][2:-1], 'regex')
    t[0] = r

def p_string_wildcard(t):
    'string : WILDCARD'
    print("SWildcard", t[1])
    w = String(t[1][2:-1], 'wildcard')
    t[0] = w

def p_error(t):
    if t is not None:
        raise ValueError("Syntax error at '%s'" % t.value())
    else:
        raise ValueError("Syntax error")

import ply.yacc as yacc
yacc.yacc()


def main():
    while 1:
        try:
            s = raw_input('input > ')
        except EOFError:
            break
        try:
            results = yacc.parse(s)
        except ValueError as e:
            print str(e)
            continue

        from pprint import pprint
        print(json.dumps(results))


if __name__ == '__main__':
    main()
