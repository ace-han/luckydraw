from django.conf import settings
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from slotmachine.luckydraw.forms import LuckyDrawSnapshotForm
from slotmachine.luckydraw.models import LuckyDrawSnapshot
from slotmachine.luckydraw.views import SESSION_SNAPSHOT_CURRENT_WINNERS_KEY, \
    SESSION_SNAPSHOT_REMAINING_KEY, SESSION_SNAPSHOT_GROUP_HASH_KEY, \
    SESSION_SNAPSHOT_4_FRONTEND_KEY
from slotmachine.staff.models import Candidate
import copy
import logging


logger = logging.getLogger(__name__)

class CreatorListFilter(SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('creator')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'creator_id'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        # below statement doesnt work out for db as in sqlite
        # list = LuckyDrawSnapshot.objects.values('created_by').distinct('created_by')
        # list = LuckyDrawSnapshot.objects.all().values_list('created_by__id', 'created_by__username').distinct('created_by__id')
        
        # for the sake of performance, a little we just take advantage of User model here since it got a small scale 
        # dependency on model User
        return User.objects.values_list('id', 'username')    

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        if(self.value()):
            queryset = queryset.filter(created_by_id__exact=self.value())
        return queryset

class LuckyDrawSnapshotAdmin(admin.ModelAdmin):
    form = LuckyDrawSnapshotForm
    list_display=('id', 'display_winner_names', 'created_time', 'display_creator', 'group_hash', )
    list_filter = ('group_hash', CreatorListFilter, )
    search_fields = ('group_hash', 'current_winners__en_name', 
                     'current_winners__zh_name', 'current_winners__department', )
    date_hierarchy = 'created_time'
    list_per_page = 20
    ordering = ('-created_time', )
    
    def display_winner_names(self, instance):
        winners = instance.current_winners.all()
        return ', '.join(winner.__unicode__() for winner in winners)
    display_winner_names.short_description = _('Winner Names')  
    
    def display_creator(self, instance):
        return instance.created_by.username
    display_creator.short_description = _('Creator')
    
    def construct_change_message(self, request, form, formsets):
        if "_restore" not in request.POST:
            return super(LuckyDrawSnapshotAdmin, self).construct_change_message(request, form, formsets)
        else: 
            return _('Restore to SnapShot %s' % form.instance.pk)
    
    def log_change(self, request, obj, message):
        """
        Log that an object has been successfully changed.

        The default implementation creates an admin LogEntry object.
        """
        if "_restore" not in request.POST:
            super(LuckyDrawSnapshotAdmin, self).log_change(request, obj, message)
        else: 
            from django.contrib.admin.models import LogEntry, CHANGE
            LogEntry.objects.log_action(
                user_id         = request.user.pk,
                content_type_id = ContentType.objects.get_for_model(obj).pk,
                object_id       = obj.pk,
                object_repr     = message,
                action_flag     = CHANGE,
                change_message  = obj.group_hash    # using change_message for restore
            )
    
    # ps: this will catch the change action only; for add actions override the response_add method in a similar way
    def response_change(self, request, obj):
        """ custom method that cacthes a new 'save and edit next' action 
            Remember that the type of 'obj' is the current model instance, so we can use it dynamically!
        """
    
        if "_restore" not in request.POST or not request.user.has_perm('luckydraw.restore_to_snapshot'):
            return super(LuckyDrawSnapshotAdmin, self).response_change(request, obj)
        else:
            remaining_ids = self._calculate_flashback_snapshot_remaining_candidate_ids(obj)
            remaining_candidates = list(Candidate.objects.filter(id__in=remaining_ids).only('id', 'en_name', 'zh_name', 'department'))
            frontend_snapshot = {SESSION_SNAPSHOT_CURRENT_WINNERS_KEY: [], 
                  SESSION_SNAPSHOT_REMAINING_KEY: remaining_candidates, 
                  SESSION_SNAPSHOT_GROUP_HASH_KEY: obj.group_hash} 
            request.session[SESSION_SNAPSHOT_4_FRONTEND_KEY] =  frontend_snapshot
            
            opts = obj._meta
            return HttpResponseRedirect(reverse('admin:%s_%s_change' % 
                                                    (opts.app_label, opts.module_name),
                                                     args=(obj.id,),
                                                     current_app=self.admin_site.name))
    
    def changelist_view(self, request, extra_context=None):
        # always false to force not display an add link on the page
        # however, you could still access the function if you are familiar with django url naming pattern^_^
        if not extra_context:
            extra_context = {}
        extra_context['has_add_permission'] = False
        return super(LuckyDrawSnapshotAdmin, self).changelist_view(request, extra_context)
    
    def _calculate_flashback_snapshot_remaining_candidate_ids(self, obj):
        # below code not going to save_model or save_related is because that
        # minus the if else in all add, change, delete view
        # since restore action is really a rare scenario, time over storage
        # reproduce the whole process
        remaining_ids = set(Candidate.objects.filter(active=True).values_list('id', flat=True))
        from django.contrib.admin.models import LogEntry
        # if in select and then in values 
        restored_snapshot_list = list(LogEntry.objects.extra(select={'created_time': 'action_time'}) \
                                            .filter(change_message=obj.group_hash,
                                                        action_time__lt=obj.created_time) \
                                        .values('object_id', 'created_time').order_by('action_time'))
            
        snapshot_list = list(LuckyDrawSnapshot.objects.filter(group_hash=obj.group_hash, 
                                                         created_time__lte=obj.created_time) \
                                            .values('id', 'current_winners__id', 'created_time') \
                                            .order_by('created_time'))
        # format to {id: xxx, current_winners__id: [...], created_time: yyyy}
        restore_snapshot_map = {}
        for snapshot in snapshot_list:
            if restore_snapshot_map.has_key(snapshot['id']):
                current_winners__id = restore_snapshot_map[snapshot['id']]['current_winners__id']
                                                    
            else: 
                current_winners__id = []
            current_winners__id.append(snapshot['current_winners__id'])
            restore_snapshot_map[snapshot['id']] = {'id': snapshot['id'], 
                                                    'current_winners__id': current_winners__id, 
                                                    'created_time': snapshot['created_time'], }
        snapshot_list = restore_snapshot_map.values()
        restore_snapshot_map.clear()
        
        # sort restored_snapshot and snapshot_list
        if len(restored_snapshot_list) > 0:
            action_history_list = sorted(restored_snapshot_list + snapshot_list, key=lambda x: x['created_time'])
            for restored_snapshot in restored_snapshot_list:
                # since we define Candidate using AutoField for id
                restore_snapshot_map[int(restored_snapshot.get('object_id'))] = None
        else: 
            action_history_list = snapshot_list
            
        for snapshot in action_history_list:
            if snapshot.get('current_winners__id'):
                winner_ids = set(snapshot.get('current_winners__id'))
                remaining_ids -= winner_ids
                if restore_snapshot_map.has_key(snapshot.get('id')):
                    restore_snapshot_map.update({snapshot.get('id'): copy.deepcopy(remaining_ids)})
            else: 
                # since we define Candidate using AutoField for id
                remaining_ids = restore_snapshot_map.get(int(snapshot.get('object_id')))
        return remaining_ids
        
    class Media:
        js = (settings.STATIC_URL + 'slotmachine/js/luckydraw/admin_fitin.js', )
    
   
admin.site.register(LuckyDrawSnapshot, LuckyDrawSnapshotAdmin)