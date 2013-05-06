# from django.views.decorators.cache import cache_page
# from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User
from django.core.cache import get_cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import simplejson
from django.utils.crypto import salted_hmac
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic.simple import direct_to_template
from slotmachine import settings
from slotmachine.luckydraw.models import LuckyDrawSnapshot
from slotmachine.staff.helpers import CandidateJSONEncoder
from slotmachine.staff.models import Candidate
import datetime
import logging
import random
import time


logger = logging.getLogger(__name__)

SESSION_SNAPSHOT_4_FRONTEND_KEY = 'luckydraw_session_snapshot_for_frontend'
SESSION_SNAPSHOT_CURRENT_WINNERS_KEY = 'luckydraw_session_current_winners'
SESSION_SNAPSHOT_REMAINING_KEY = 'luckydraw_session_remaining_candidates'
SESSION_SNAPSHOT_GROUP_HASH_KEY = 'luckydraw_session_group_hash'



#@cache_page(60*15)
@ensure_csrf_cookie
def index(request):
    return direct_to_template(request, 'luckydraw/index.html', locals());

@permission_required('luckydraw.add_luckydrawsnapshot')
def init(request):
    # may do some access control here, by the day comes
    # or just simply disable the lucky draw account
    frontend_snapshot = request.session.get(SESSION_SNAPSHOT_4_FRONTEND_KEY, None)
    if not frontend_snapshot:
        # init here
        # load the necessary fields
        key_salt = 'luckydrawsnapshot'
        info = ('luckydraw.views', str(time.time()))
        value = "-".join(info)
        group_hash = salted_hmac(key_salt, value).hexdigest()
        
        candidates = []
        # for unknown reason, we might as well ensure queryset to candidates. Need to figure out later
        for c in Candidate.objects.filter(active=True).only('id', 'en_name', 'zh_name', 'department'):
            candidates.append(c)
        
        frontend_snapshot = {SESSION_SNAPSHOT_CURRENT_WINNERS_KEY: [], 
                  SESSION_SNAPSHOT_REMAINING_KEY: candidates, 
                  SESSION_SNAPSHOT_GROUP_HASH_KEY: group_hash}  #this field is just for db logging
        request.session[SESSION_SNAPSHOT_4_FRONTEND_KEY] =  frontend_snapshot
    return HttpResponse(simplejson.dumps(frontend_snapshot[SESSION_SNAPSHOT_REMAINING_KEY], cls=CandidateJSONEncoder), mimetype='application/json')


@permission_required('luckydraw.add_luckydrawsnapshot')
def get_winners(request, count):
    '''
    return a json {current_winners: [Candidate0, Candidate1, ...], 
                    remaining_candidates:[CandidateX, CandidateY, ...]}
    '''
    count = int(count) > 0 and int(count) or 1
    count = count > settings.WINNER_COUNT_AT_A_TIME and settings.WINNER_COUNT_AT_A_TIME or count
    
    frontend_snapshot = request.session.get(SESSION_SNAPSHOT_4_FRONTEND_KEY)
    
    if not frontend_snapshot:
        logger.warning('Requesting get_winners method without key: %s, redirecting...', 
                       SESSION_SNAPSHOT_4_FRONTEND_KEY)
        return HttpResponseRedirect(reverse(index))
    
    remaining_candidates = frontend_snapshot.get(SESSION_SNAPSHOT_REMAINING_KEY)
    if len(remaining_candidates) < count:
        return HttpResponse(simplejson.dumps({'error': 
                        'Running out of candidates, remaining:%s, requesting:%s.' % (len(remaining_candidates), count)
                        + '\n You could either clear session cookies and refresh the page to start all over again '
                        + 'or turn down the requesting amount' ,
                         SESSION_SNAPSHOT_REMAINING_KEY: remaining_candidates}, cls=CandidateJSONEncoder), mimetype='application/json')
    
    current_winners = frontend_snapshot[SESSION_SNAPSHOT_CURRENT_WINNERS_KEY]
    # clear the list
    del current_winners[:]
    
    # core algorithm...
    
    # shuffle every time in order to avoid the sequence remain the same 
    # when looping in front-end
    random.shuffle(remaining_candidates)
    for i in range(0, count):
        winner = random.choice(remaining_candidates)
        current_winners.append(winner)
        remaining_candidates.remove(winner)

    # seems need to manually update the session
    request.session[SESSION_SNAPSHOT_4_FRONTEND_KEY] = frontend_snapshot
    __save_snapshot(request, frontend_snapshot)
    
    return HttpResponse(simplejson.dumps(frontend_snapshot, cls=CandidateJSONEncoder), mimetype='application/json')

def query_restore_perm(request):
    # to avoid explode the function code directly from frontend js code
    return HttpResponse('<input type="submit" name="_restore" value="Restore" title="restore remaining candidates as snapshot"/>' \
                         if request.user.has_perm('luckydraw.restore_to_snapshot') else 0)


# might do it in a multi-thread fashion
def __save_snapshot(request, frontend_snapshot):
    if request.user.is_anonymous() and not isinstance(request.user, User):
        cache = get_cache('default')
        anonymous_user = cache.get('anonymous_user')
        if not anonymous_user:
            try:
                anonymous_user = User.objects.get(username=settings.ANONYMOUS_USER_NAME)
            except ObjectDoesNotExist:
                logger.warning('Please setup ANONYMOUS_USER_NAME in settings.py file.\nThis snapshot won\'t be saved in db')
                return
            cache.set('anonymous_user', anonymous_user)
        request.user = anonymous_user
    snapshot = LuckyDrawSnapshot(group_hash=frontend_snapshot[SESSION_SNAPSHOT_GROUP_HASH_KEY], 
                                 created_time=datetime.datetime.now(), created_by=request.user)
    snapshot.save()
    snapshot.current_winners.add(*frontend_snapshot[SESSION_SNAPSHOT_CURRENT_WINNERS_KEY])
    