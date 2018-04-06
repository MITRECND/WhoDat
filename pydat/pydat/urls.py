from django.conf.urls import url
from django.conf import settings
from pydat import ajax, views

urlpatterns = [
  url(r'^$', views.index, name='index'),

  url(r'^domains/(?P<key>.*)/(?P<value>.*)/$', views.domains),
  url(r'^domains/$', views.domains, name='domains'),

  url(r'^pdns_results/(?P<search_value>.*)/$', views.pdns, name='pdns_rest'),
  url(r'^pdns_results/$', views.pdns, name='pdns_results'),
  url(r'^pdns_search/$', views.pdns_index, name='pdns'),

  url(r'^pdnsr_results/(?P<search_value>.*)/$', views.pdns_r, name='pdns_r_rest'),
  url(r'^pdnsr_results/$', views.pdns_r, name='pdns_r_results'),
  url(r'^pdnsr_search/$', views.rpdns_index, name='pdns_r'),

  url(r'^ajax/metadata/$', ajax.metadata),
  url(r'^ajax/metadata/(?P<version>.*)/$', ajax.metadata),

  url(r'^ajax/domain/(?P<domainName>.*)/diff/(?P<v1>.*)/(?P<v2>.*)/$', ajax.domain_diff),
  url(r'^ajax/domain/(?P<domainName>.*)/(?P<low>.*)/(?P<high>.*)/$', ajax.domain),
  url(r'^ajax/domain/(?P<domainName>.*)/latest/$', ajax.domain_latest),
  url(r'^ajax/domain/(?P<domainName>.*)/(?P<low>.*)/$', ajax.domain),
  url(r'^ajax/domain/(?P<domainName>.*)/$', ajax.domain),
  url(r'^ajax/domain/$', ajax.domain, name='ajax_domain'),

  url(r'^ajax/domains/(?P<key>.*)/(?P<value>.*)/(?P<low>.*)/(?P<high>.*)/$', ajax.domains ),
  url(r'^ajax/domains/(?P<key>.*)/(?P<value>.*)/latest/$', ajax.domains_latest ),
  url(r'^ajax/domains/(?P<key>.*)/(?P<value>.*)/(?P<low>.*)/$', ajax.domains ),
  url(r'^ajax/domains/(?P<key>.*)/(?P<value>.*)/$', ajax.domains ),
  url(r'^ajax/domains/$', ajax.domains, name='ajax_domains'),

  url(r'^ajax/dataTable/(?P<key>.*)/(?P<value>.*)/(?P<low>.*)/(?P<high>.*)/$', ajax.dataTable ),
  url(r'^ajax/dataTable/$', ajax.dataTable, name='ajax_dataTable'),


  url(r'^ajax/resolve/(?P<domainName>.*)/$', ajax.resolve),
  url(r'^ajax/resolve/$', ajax.resolve, name='ajax_resolve'),

  url(r'^advdomains/$', views.advdomains, name='advdomains'),
  url(r'^ajax/query/$', ajax.advanced_search, name='ajax_advanced'),
  url(r'^ajax/advDataTable/$', ajax.advDataTable, name='ajax_advDataTable'),
  url(r'^stats/$', views.stats, name='stats'),
  url(r'^help/$', views.help, name='help'),
]
