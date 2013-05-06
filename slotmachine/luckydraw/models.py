from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _
from slotmachine.staff.models import Candidate

class LuckyDrawSnapshot(models.Model):
    '''
    As a snapshot for every lucky draw 
    '''
    group_hash = models.CharField(max_length=64) # take this as a group mark
    current_winners = models.ManyToManyField(Candidate) 
    created_time = models.DateTimeField()
    created_by = models.ForeignKey(User)
    
#    def __unicode__(self):
#        return 'group_hash: ' + self.group_hash \
#                    + '\ncreated_time: ' + self.created_time.strftime('%c') \
#                    + '\ncreated_by: ' + self.created_by.name 
    
    
    class Meta:
        db_table = 'luckydraw_snapshot'
        verbose_name = _('Lucky Draw Snapshot')
        permissions = (('restore_to_snapshot',  _('Can restore remaining candidates as snapshot')),)