#!/usr/bin/env python
import re
from ply.lex import TOKEN
import json
import datetime

tokens = [
    'COLON',
    'WORD',
    'QUOTED',
    'NOT',
    'OR',
    'AND',
    'LPAREN',
    'RPAREN',
    'FUZZY',
    'REGEX',
    'WILDCARD',
    'DATE',
    'NULL'
]

regex_pattern = r'(r"(\\.|[^\t\n\r\f\v"])+")|' + r"(r'(\\.|[^\t\n\r\f\v'])+')"
wildcard_pattern = r'(w"([^\t\n\r\f\v"])+")|' + r"(w'([^\t\n\r\f\v'])+')"

# Tokens
# Regex precendence is functions in file order followed by regex
# strings with decreasing complexity
t_QUOTED = (r'"(\\[\\"~:\(\)]|[^\t\n\r\f\v\\"~:\(\)])+"|' +
            r"'(\\[\\~':\(\)]|[^\t\n\r\f\v\\'~:\(\)])*'")
t_WORD = r'((\\[\\~:\(\)])|[^\s\\~:\(\)\'"])+'
t_DATE = r'[0-9]{4}-((0[1-9])|1[0-2])-((0[1-9])|([1-2][0-9])|(3[0-1]))'
t_FUZZY = r'~[0-9]?'
t_COLON = r':'
t_LPAREN = r'\('
t_RPAREN = r'\)'


@TOKEN(regex_pattern)
def t_REGEX(t):
    return t


@TOKEN(wildcard_pattern)
def t_WILDCARD(t):
    # Need to check manually since otherwise the token won't match properly
    if ' ' in t.value:
        t_error(t)
        return None
    return t


@TOKEN('NOT')
def t_NOT(t):
    return t


@TOKEN('OR')
def t_OR(t):
    return t


@TOKEN('AND')
def t_AND(t):
    return t


@TOKEN('!NULL!')
def t_NULL(t):
    return t


t_ignore = " \t\n"

# def t_newline(t):
#     r'\n+'
#     t.lexer.lineno += t.value.count("\n")


def t_error(t):
    if t is not None:
        raise ValueError(
            "Unexpected character(s)/sequence at position %d: %s"
            % (t.lexpos, t.value))
    else:
        raise ValueError("Unable to parse input")


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
      | NOT query
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
         | WORD COLON NULL

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
    'details.administrativeContact_telephoneExt'
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
    'contactEmail',
    'nameServers',
    'registrarName',
    'whoisServer'
]

special_keywords = {
    'email_local': [
        "details.administrativeContact_email.local",
        "details.registrant_email.local",
        "details.contactEmail.local",
    ],
    'email_domain': [
        "details.administrativeContact_email.domain",
        "details.registrant_email.domain",
        "details.contactEmail.domain",
    ]
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
    'email': [
        "details.administrativeContact_email",
        "details.registrant_email",
        "details.contactEmail",
    ],
    'name': [
        'details.administrativeContact_name',
        'details.registrant_name'
    ],
    'organization': [
        'details.administrativeContact_organization',
        'details.registrant_organization'
    ],
    'street': [
        'details.registrant_street1',
        'details.registrant_street2',
        'details.registrant_street3',
        'details.registrant_street4',
        'details.administrativeContact_street1',
        'details.administrativeContact_street2',
        'details.administrativeContact_street3',
        'details.administrativeContact_street4',
    ],
    'city': [
        'details.administrativeContact_city',
        'details.registrant_city'
    ],
    'state': [
        'details.administrativeContact_state',
        'details.registrant_state'
    ],
    'postalCode': [
        'details.administrativeContact_postalCode',
        'details.registrant_postalCode'
    ],
    'country': [
        'details.administrativeContact_country',
        'details.registrant_country'
    ],
    'telephone': [
        'details.administrativeContact_telephone',
        'details.registrant_telephone'
    ],
    'telephoneExt': [
        'details.administrativeContact_telephoneExt',
        'details.registrant_telephoneExt'
    ],
    'fax': [
        'details.administrativeContact_fax',
        'details.registrant_fax'
    ],
    'faxExt': [
        'details.administrativeContact_faxExt',
        'details.registrant_faxExt'
    ],
    'ns': ['details.nameServers'],
    'registrar': ['details.registrarName'],
}


def p_query_group(t):
    'query : LPAREN query RPAREN'
    t[0] = t[2]


def p_query_not(t):
    'query : NOT query'

    t[0] = {
        "query": {
            "bool": {
                "must_not": [{'bool': t[2]['query']['bool']}],
            }
        }
    }


def create_combined_and(query1, query2):
    return {
        "query": {
            "bool": {
                "must": [{'bool': query1['query']['bool']},
                         {'bool': query2['query']['bool']}]
            }
        }
    }


def p_query_query(t):
    'query : query query %prec AND'
    t[0] = create_combined_and(t[1], t[2])


def p_query_and_query(t):
    'query : query AND query'
    t[0] = create_combined_and(t[1], t[3])


def p_query_or_query(t):
    'query : query OR query'

    t[0] = {
        "query": {
            "bool": {
                "should": [{'bool': t[1]['query']['bool']},
                           {'bool': t[3]['query']['bool']}],
                "disable_coord": "true"
            }
        }
    }


def p_query_terminals(t):
    '''query : specific
             | daterange
             | termquery'''
    t[0] = t[1]


def create_specific_word_subquery(key, value):
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
            raise KeyError("Unknown field %s" % key)

        nf = []
        for f in fields1:
            if f not in no_parts:
                f += ".parts"
            nf.append(f)
        fields1 = nf

    q = {
        'multi_match': {
            "query": value,
            "fields": fields1
        }
    }

    return q


def p_specific_fuzzy_word(t):
    'specific : FUZZY WORD COLON WORD'

    key = t[2]
    value = t[4]
    if len(t[1]) == 1:
        fuzzy = 'AUTO'
    else:
        fuzzy = int(t[1][1])
    value = remove_escapes(value)

    sub_query = create_specific_word_subquery(key, value)
    sub_query['multi_match']['fuzziness'] = fuzzy

    t[0] = {'query': {'bool': {'must': [sub_query]}}}


def p_specific_word(t):
    'specific : WORD COLON WORD'

    key = t[1]
    value = t[3]
    value = remove_escapes(value)

    sub_query = create_specific_word_subquery(key, value)

    t[0] = {'query': {'bool': {'must': [sub_query]}}}


def p_specific_fuzzy_quoted(t):
    'specific : FUZZY WORD COLON QUOTED'
    key = t[2]
    value = t[4]
    if len(t[1]) == 1:
        fuzzy = 'AUTO'
    else:
        fuzzy = int(t[1][1])

    value = remove_escapes(value[1:-1])
    value = value.lower()

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

        nf = []
        for f in fields1:
            if f not in no_parts:
                f += ".parts"
            nf.append(f)
        fields1 = nf

    q = {
        'multi_match': {
            "query": str(value),
            "fields": fields1,
            "fuzziness": fuzzy
        }
    }

    t[0] = {'query': {'bool': {'must': [q]}}}


def p_specific_quoted(t):
    'specific : WORD COLON QUOTED'

    key = t[1]
    value = t[3]

    value = remove_escapes(value[1:-1])
    value = value.lower()

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

    q = {}
    split_vals = value.split()
    shds = []
    for f in fields1:
        shd = {'term': {f: {"value": value, "boost": 1.5}}}
        shds.append(shd)

    for f in fields2:
        if len(split_vals) > 1:
            spans = []
            for p in split_vals:
                spans.append({'span_term': {f: p}})
            shds.append({'span_near': {
                'clauses': spans, 'slop': 1, 'in_order': 'true'}})
        else:
            shd = {'term': {f: {"value": value}}}
            shds.append(shd)

    if len(shds) == 1:
        q['query'] = shds[0]
    else:
        # q['bool'] = {'should': shds}
        q['dis_max'] = {'queries': shds}

    if 'query' not in q:
        t[0] = {'query': {'bool': {'must': [q]}}}
    else:
        t[0] = {'query': {'bool': {'must': [q['query']]}}}


def p_field_missing(t):
    'specific : WORD COLON NULL'

    key = t[1]

    fields = []
    if key in special_keywords:
        fields = special_keywords[key]
    else:
        if key in shortcut_keywords:
            fields = shortcut_keywords[key]
        elif key in original_keywords:
            if key != 'domainName':
                key = 'details.' + key
            fields = [key]
        else:
            raise KeyError("Unknown field")

    print(fields)
    must_nots = []
    for f in fields:
        mn = {'exists': {"field": f}}
        must_nots.append(mn)

    t[0] = {'query': {'bool': {'must_not': must_nots}}}


def create_wildreg_query(key, value, qtype):
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

    q = {}
    shds = []
    for f in fields1:
        shd = {qtype: {f: {"value": str(value), "boost": 1.5}}}
        shds.append(shd)
    for f in fields2:
        shd = {qtype: {f: str(value)}}
        shds.append(shd)
    if len(shds) == 1:
        q['query'] = shds[0]
    else:
        # q['bool'] = {'should': shds}
        q['dis_max'] = {'queries': shds}

    if 'query' not in q:
        return {'query': {'bool': {'must': [q]}}}
    else:
        return {'query': {'bool': {'must': [q['query']]}}}


def p_specific_wildcard(t):
    'specific : WORD COLON WILDCARD'

    key = t[1]
    value = t[3][2:-1]

    t[0] = create_wildreg_query(key, value, 'wildcard')


def p_specific_regex(t):
    'specific : WORD COLON REGEX'

    key = t[1]
    value = t[3][2:-1]

    t[0] = create_wildreg_query(key, value, 'regexp')


def create_daterange_query(key, start, end):
    if key not in date_keywords:
        raise KeyError("Unknown Key")
    key = date_keywords[key]
    qf = {
        'query': {'bool': {'filter': {
            'range': {
                key: {
                    'gte': start.strftime('%Y-%m-%d %H:%M:%S'),
                    'lt': end.strftime('%Y-%m-%d %H:%M:%S'),
                }
            }}}}}

    return qf


def p_daterange_single(t):
    'daterange : WORD COLON DATE'

    try:
        start = datetime.datetime.strptime(t[3], '%Y-%m-%d')
    except Exception as e:
        raise ValueError("Invalid Date Format: %s" % str(e))

    end = start + datetime.timedelta(1, 0)

    t[0] = create_daterange_query(t[1], start, end)


def p_daterange_range(t):
    'daterange : WORD COLON DATE COLON DATE'

    try:
        start = datetime.datetime.strptime(t[3], '%Y-%m-%d')
        end = (datetime.datetime.strptime(t[5], '%Y-%m-%d') +
               datetime.timedelta(1, 0))
    except Exception as e:
        raise ValueError("Invalid Date Range")

    if end < start:
        raise ValueError("End date less than start date")

    t[0] = create_daterange_query(t[1], start, end)


def p_termquery_quoted(t):
    '''termquery : QUOTED'''

    term = remove_escapes(t[1][1:-1])
    term = term.lower()
    query = None
    terms = term.split()

    ll = looks_like(term)
    if ll is None:
        if len(terms) > 1:
            spns = []
            for p in terms:
                spns.append({'span_term': {'pydat_all': p}})
            query = {'span_near': {
                'clauses': spns, 'slop': 1, 'in_order': 'true'}}
        else:
            query = {'term': {'pydat_all': term}}
    else:
        if ll == 'email':
            fields = [
                       ("details.administrativeContact_email.parts", 1.5),
                       ("details.registrant_email.parts", 1.5),
                       ("details.contactEmail.parts", 1.5),
                       ("pydat_all", 1.0)
                     ]
        elif ll == 'domain':
            fields = [
                       ("domainName.parts", 2.0),
                       ("details.administrativeContact_email.parts", 1.5),
                       ("details.registrant_email.parts", 1.5),
                       ("details.contactEmail.parts", 1.5),
                       ("pydat_all", 1.0)
                     ]

        queries = []
        for (f, boost_val) in fields:
            if len(terms) > 1:
                spans = []
                for p in terms:
                    spans.append({'span_term': {f: p}})
                queries.append({'span_near': {
                    'clauses': spans, 'slop': 1,
                    'in_order': 'true', 'boost': boost_val}})
            else:
                shd = {'term': {f: {"value": terms[0], 'boost': boost_val}}}
                queries.append(shd)

        query = {'dis_max': {'queries': queries}}

    t[0] = {"query": {"bool": {"must": [query]}}}


def p_termquery_word(t):
    '''termquery : WORD'''

    term = remove_escapes(t[1])
    query = None
    ll = looks_like(term)
    if ll is None:
        query = {'match': {'pydat_all': term}}
    else:
        if ll == 'email':
            fields = [
                "details.administrativeContact_email.parts^2",
                "details.registrant_email.parts^2",
                "details.contactEmail.parts^2",
                "pydat_all"]
        elif ll == 'domain':
            fields = [
                "domainName.parts^3",
                "details.administrativeContact_email.parts^2",
                "details.registrant_email.parts^2",
                "details.contactEmail.parts^2",
                "pydat_all"]

        query = {
            "multi_match": {
                "query": term,
                "fields": fields
            }
        }

    t[0] = {"query": {"bool": {"must": [query]}}}


def remove_escapes(t):
    unescaped_string = ""
    parts = re.split(r'(\\.)', t)
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
        raise ValueError(
            "Syntax error at position %d: %s" % (t.lexpos, t.value))
    else:
        raise ValueError("Syntax error")


precedence = (
        ('left', 'AND', 'OR'),
        ('right', 'NOT'),
        ('left', 'COLON'),
    )

import ply.yacc as yacc
yacc.yacc(debug=False)


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
