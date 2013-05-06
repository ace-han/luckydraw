from django.conf.urls import patterns, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('slotmachine.luckydraw.views',
    # BAD URL NAMING Pattern!!!
    url(r'^perm/restore/$',                     'query_restore_perm',   name='luckydraw-query-restore-perm'),
    url(r'^get-winners/(?P<count>\d{,2})/$',    'get_winners',          name='luckydraw-get-winners'),
    url(r'^init/$',                             'init',                 name='luckydraw-init'),
    url(r'^index/?$',                           'index',                name='luckydraw-index'),
    url(r'^$',                                  'index',                name='luckydraw-entrance'),
)
