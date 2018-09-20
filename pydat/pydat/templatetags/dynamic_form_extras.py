from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

'''
for an index integer N, returns the string "sourceN".
(Returned string is utilized for matching passive-DNS source form fields
to corresponding panels. Each passive-DNS source has its own html 
panel which is then filled with fields that are binded to it via an ID)
'''

@register.filter
@stringfilter
def source_id(pdns_index):
    return "source" + str(pdns_index)

@register.filter('prefix')
def prefix(data, pre):
    try:
        return data.startswith(pre)
    except:
        pass
    return False
