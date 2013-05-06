from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _

class Candidate(models.Model):
    en_name = models.CharField(_('English Name'), max_length=64) 
    zh_name = models.CharField(_('Chinese Name'), max_length=64, null=True, blank=True)
    department = models.CharField(max_length=128)
    active = models.BooleanField(default=True)
    created_time = models.DateTimeField()
    created_by = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, related_name='ccandidated_set')
    last_modified_time = models.DateTimeField()
    last_modified_by = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, related_name='mcandidated_set')
    next = None # for frontend simplification
    
    def __unicode__(self):
        return (self.en_name or '') + ' ' + (self.zh_name or '')
                    
    class Meta:
        unique_together = ('en_name', 'zh_name', 'department', )