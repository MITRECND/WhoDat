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

query : LPAREN query RPAREN
      | query query
      | query AND query
      | query OR query
      | specific
      | daterange
      | termquery

specific : FUZZY WORD COLON WORD
         | WORD COLON WORD
         | FUZZY WORD COLON QUOTED
         | WORD COLON QUOTED
         | WORD COLON REGEX
         | WORD COLON WILDCARD

daterange : WORD COLON DATE
          | WORD COLON DATE COLON DATE

termquery : QUOTED
          | WORD 

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
    '''query : query query %prec AND
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



def p_query_terminals(t):
    '''query : specific
             | daterange
             | termquery'''
    print('QSpec', t[1])
    t[0] = t[1]


def p_specific_word(t):
    '''specific : FUZZY WORD COLON WORD
                | WORD COLON WORD'''

    if len(t) == 5:
        key = t[2]
        value = t[4]
        if len(t[1]) == 1:
            fuzzy = 'AUTO'
        else:
            fuzzy = int(t[1][1])
    else:
        key = t[1]
        value = t[3]
        fuzzy = None

    print('SWord', key, value, fuzzy)

    value = remove_escapes(value)


    fields1 = []
    if key in special_keywords:
        fields1 = special_keywords[key]
    else:
        if key in shortcut_keywords:
            fields1 = shortcut_keywords[key]
        elif key in original_keywords:
            if key != 'domainName':
                key = 'details.' + key
            fields1 = [key]
        else:
            raise KeyError("Unknown field")

        nf = []
        for f in fields1:
            if f not in no_parts:
                f += ".parts"
            nf.append(f)
        fields1 = nf

    print fields1

    q = {
        'multi_match': {
            "query": value,
            "fields": fields1 
        }
    } 

    if fuzzy is not None:
        q['multi_match']['fuzziness'] = fuzzy

    t[0] = {'query': {'filtered': {'filter': {'match_all': {}}, 'query': q}}}

def p_specific_quoted(t):
    '''specific : FUZZY WORD COLON QUOTED
                | WORD COLON QUOTED'''

    if len(t) == 5:
        key = t[2]
        value = t[4]
        if len(t[1]) == 1:
            fuzzy = 'AUTO'
        else:
            fuzzy = int(t[1][1])
    else:
        key = t[1]
        value = t[3]
        fuzzy = None

    print('SQuoted', key, value, fuzzy)
    value = remove_escapes(value[1:-1])

    fields1 = []
    fields2 = []

    if key in special_keywords:
        fields1 = special_keywords[key]
    else:
        if key in shortcut_keywords:
            fields1 = shortcut_keywords[key]
        elif key in original_keywords:
            if key != 'domainName':
                key = 'details.' + key
            fields1 = [key]
        else:
            raise KeyError("Unknown field")

            
        if  fuzzy is not None:
            nf = []
            for f in fields1:
                if f not in no_parts:
                    f += ".parts"
                nf.append(f)
            fields1 = nf
        else:
            for f in fields1:
                if f not in no_parts:
                    f += ".parts"
                    fields2.append(f)


    print fields1, fields2

    q = {}
    
    if fuzzy is None:
        split_vals = value.split()
        shds = []
        for f in fields1:
            shd = {'term': { f: {"value": value, "boost" : 1.5}}}
            shds.append(shd)

        for f in fields2:
            if len(split_vals) > 1:
                spans = []
                for p in split_vals:
                    spans.append({'span_term': {f:p}})
                shds.append({'span_near': { 'clauses': spans, 'slop': 1, 'in_order': 'true'}})
                '''
                musts = []
                for p in split_vals:
                    musts.append({'term': {f: p}})
                shds.append({'bool': {'must': musts}})
                '''
            else:
                shd = {'term': {f: {"value": value}}}
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

def p_specific_wildcard_regex(t):
    '''specific : WORD COLON WILDCARD
                | WORD COLON REGEX'''

    key = t[1]
    value = t[3][2:-1]
    rorw = t[3][0]
    
    print('SWord', key, value)

    fields1 = []
    fields2 = []

    if key in special_keywords:
        fields1 = special_keywords[key]
    else:
        if key in shortcut_keywords:
            fields1 = shortcut_keywords[key]
        elif key in original_keywords:
            if key != 'domainName':
                key = 'details.' + key
            fields1 = [key]
        else:
            raise KeyError("Unknown field")

        for f in fields1:
            if f not in no_parts:
                f += ".parts"
                fields2.append(f)

    print fields1, fields2

    q ={}

    shds = []
    if rorw == 'w':
        qtype = 'wildcard'
    else:
        qtype = 'regexp'

    for f in fields1:
        shd = {qtype: {f: {"value": str(value), "boost": 1.5}}}
        shds.append(shd)
    for f in fields2:
        shd = {qtype: {f: str(value)}}
        shds.append(shd)
    if len(shds) == 1:
        q['query'] =  shds[0]
    else:
        q['bool'] = {'should': shds}

    if 'query' not in q:
        t[0] = {'query': {'filtered': {'filter': {'match_all': {}}, 'query': q}}}
    else:  
        t[0] = {'query': {'filtered': {'filter': {'match_all': {}}, 'query': q['query']}}}

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

def p_termquery_quoted(t):
    '''termquery : QUOTED'''
    print('TermQueryQ', t[1])

    term = remove_escapes(t[1][1:-1])
    if ' ' in term:
        whitespace = True
    else:
        whitespace = False

    parts = []

    ll = looks_like(term)
    if ll is None:
        #XXX TODO use span queries?
        for p in term.split():
            parts.append({'term': {'_all': p }})
    else:
        if ll == 'email':
            fields = [ "details.administrativeContact_email.parts", 
                       "details.registrant_email.parts", 
                       "_all" ] 
        elif ll == 'domain':
            fields = [ "domainName.parts^3",
                       "details.administrativeContact_email.parts", 
                       "details.registrant_email.parts", 
                       "_all"]

        terms = term.split()
        if len(terms) > 1:
            terms.append(term)
        else:
            terms = [term]

        print terms

        for p in terms:
            shds = []
            for f in fields:
                 shds.append({'term': {f:p}})
            if len(shds) > 1:
                parts.append({'bool': {'should': shds}})
            else:
                parts.append(shds[0])

    if len(parts) == 1:
        t[0] = {"query": {"filtered": {"query": parts[0], "filter": {"match_all":{}}}}}
    else:
        t[0] = {"query": {"filtered": {"query": {"bool": {"must" : parts }}, "filter": {'match_all': {}}}}}

def p_termquery_word(t):
    '''termquery : WORD'''
    print('TermQueryW', t[1])

    term = remove_escapes(t[1])

    parts = []

    ll = looks_like(term)
    if ll is None:
        parts.append({'match': {'_all': term}})
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

        parts.append({
            "multi_match": {
                "query": term,
                "fields": fields
            }
        })

    if len(parts) == 1:
        t[0] = {"query": {"filtered": {"query": parts[0], "filter": {"match_all":{}}}}}
    else:
        t[0] = {"query": {"filtered": {"query": {"bool": {"must" : parts }}, "filter": {'match_all': {}}}}}


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

def p_error(t):
    if t is not None:
        raise ValueError("Syntax error at '%s'" % t)
    else:
        raise ValueError("Syntax error")

precedence = (
        ('left', 'AND', 'OR'),
        ('left', 'COLON'),
    )

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
        except KeyError as e:
            print str(e)
            continue

        print(json.dumps(results))


if __name__ == '__main__':
    main()
