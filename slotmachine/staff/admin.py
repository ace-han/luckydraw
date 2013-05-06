from django.contrib import admin
from django.core.files.storage import FileSystemStorage
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _, ungettext
from slotmachine import settings
from slotmachine.staff.forms import CandidateForm
from slotmachine.staff.models import Candidate
from xlrd.biffh import XLRDError
import datetime
import os.path


class CandidateAdmin(admin.ModelAdmin):
    form = CandidateForm
    list_display=('en_name', 'zh_name','department', 'active', 'last_modified_time', 'last_modified_by')
    list_filter = ['department', 'active']
    readonly_fields = ('created_time', 'created_by', 'last_modified_time', 'last_modified_by')
    search_fields = ['en_name', 'zh_name', 'department']
    date_hierarchy = ('last_modified_time')
    actions = ['perform_activate', 'perform_deactivate']
    list_per_page = 20
    list_select_related =True
    ordering = ('-last_modified_time','-created_time', )
    
    uploadfile_storage  = FileSystemStorage(os.path.join(settings.MEDIA_ROOT, 'excel'))
    
    def _prepare_misc_info(self, new_object, 
                           created_time=datetime.datetime.now(), 
                           created_by=None, 
                           last_modified_time=None, 
                           last_modified_by=None):
        new_object.created_time = created_time
        new_object.created_by = created_by
        new_object.last_modified_time = bool(last_modified_time) and last_modified_time or created_time
        new_object.last_modified_by = bool(last_modified_by) and last_modified_by or created_by
    
    def _prepare_candidate(self, en_name, 
                           zh_name,
                           department,
                           creator,
                           created_time=datetime.datetime.now()):
        c = Candidate()
        c.en_name = en_name or ''
        c.zh_name = zh_name or ''
        c.department = department or ''
        self._prepare_misc_info(c, created_time, creator)
        return c
        
    def _prepare_candidate_via_upload_file(self, file_contents, creator):
        import xlrd
        # since we are using InMemoryUploadedFile just read() instead of chunks()
        wb = xlrd.open_workbook(file_contents=file_contents)
        try:
            sheet = wb.sheet_by_name('candidate')
        except XLRDError, e:
            sheet = wb.sheet_by_index(0)
        now = datetime.datetime.now()
        candidate_map = {} # using dict for unification
        for row in range(sheet.nrows)[1:]:
            en_name = sheet.cell(row, 0).value.strip()
            zh_name = sheet.cell(row, 1).value.strip()
            department = sheet.cell(row, 2).value.strip()
            candidate_map[en_name+zh_name+department] = self._prepare_candidate(en_name, 
                                                                                zh_name, 
                                                                                department, 
                                                                                creator,
                                                                                now)
        copy = dict(candidate_map)  # make a copy to avoid RuntimeError while deletion on the fly
        for k, v in copy.items():
            # great db access, poor performance. Better think of another approach  
            if Candidate.objects.filter(en_name=v.en_name, 
                                     zh_name=v.zh_name, 
                                     department=v.department).exists():
                del candidate_map[k]
        
        return candidate_map.values()
    
    def save_model(self, request, obj, form, change):
        upload_file = form.cleaned_data.get('candidate_list')
        if not upload_file:
            self._prepare_misc_info(obj, created_by=request.user)
            super(CandidateAdmin, self).save_model(request, obj, form, change)
        else:
            file_contents = bytearray(upload_file.read())
            # save the uploaded_file to file system for record
            self.uploadfile_storage.save('%s-%s-%s' % (datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
                                                      request.user.username,
                                                      upload_file.name),
                                         upload_file)
            
            new_candidates = self._prepare_candidate_via_upload_file(file_contents, request.user)
            added_count = len(new_candidates)
            # we might as well use COOKIE for msg carrier since GET/POST/REQUEST immutable
            request.COOKIES['added_count'] = added_count 
            Candidate.objects.bulk_create(new_candidates, batch_size=100)
#            batch_size  = 50# Bulk model save db
#            batch_count = len(new_candidates)%batch_size and (len(new_candidates)/batch_size+1) or len(new_candidates)/batch_size  
#            for i in range(batch_count):
#                Candidate.objects.bulk_create(new_candidates[i*batch_size:(i+1)*batch_size])
            obj.en_name = ungettext('One candidate via upload %(upload_file)s',
                            '%(count)d candidates via upload %(upload_file)s',
                            added_count) % {'count': added_count, 'upload_file': upload_file.name}
            
            
            
    def response_add(self, request, obj, post_url_continue='../%s/'):
        """
        Determines the HttpResponse for the add_view stage.
        """
        opts = obj._meta
        if request.COOKIES.get('added_count') is not None:
            msg = ungettext('One candidate added successfully.',
                            '%(count)d candicates added successfully.',
                            request.COOKIES.get('added_count')) % {'count': request.COOKIES.get('added_count')}
            del request.COOKIES['added_count']
            
            self.message_user(request, msg)
            if self.has_change_permission(request, None):
                post_url = reverse('admin:%s_%s_changelist' %
                                   (opts.app_label, opts.module_name),
                                   current_app=self.admin_site.name)
            else:
                post_url = reverse('admin:index',
                                   current_app=self.admin_site.name)
            return HttpResponseRedirect(post_url)
        else: 
            return super(CandidateAdmin, self).response_add(request, obj, post_url_continue)
        
       
    def perform_activate(self, request, queryset):
        updated = queryset.update(active=True, last_modified_time=datetime.datetime.now(),
                                  last_modified_by=request.user)
        msg = ungettext('there is %(updated)d object activated', 
                         'there are %(updated)d objects activated', 
                         updated)
        self.message_user(request, msg % {'updated': updated})
    perform_activate.short_description= _("Activate selected candidate(s)")
    
    def perform_deactivate(self, request, queryset):
        updated = queryset.update(active=False, last_modified_time=datetime.datetime.now(),
                                  last_modified_by=request.user)
        msg = ungettext('there is %(updated)d object deactivated', 
                         'there are %(updated)d objects deactivated', 
                         updated)
        self.message_user(request, msg % {'updated': updated})
    perform_deactivate.short_description= _("Deactivate selected candidate(s)")
    
    #Edit Page
    fieldsets=(
               (_('Candidate'), 
                    {'fields': ('en_name', 'zh_name', 'department', 'active')}
                ),
               (_('Misc. Info.'), 
                    {'fields': ('created_time', 'created_by', 'last_modified_time', 'last_modified_by')}
                ),
               (_('Batch Upload'), 
                    {'fields': ('candidate_list', )}
                ),
              )

admin.site.register(Candidate, CandidateAdmin)