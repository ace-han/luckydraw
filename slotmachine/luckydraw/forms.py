from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.forms.util import ErrorList
from django.utils.translation import ugettext_lazy as _
from slotmachine.luckydraw.models import LuckyDrawSnapshot
from slotmachine.staff.models import Candidate

class LuckyDrawSnapshotForm(forms.ModelForm):
    current_winners = forms.ModelMultipleChoiceField(queryset=Candidate.objects.none())
    
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, instance=None):
        
        super(LuckyDrawSnapshotForm, self).__init__(data, files, auto_id, prefix,
                 initial, error_class, label_suffix, empty_permitted, instance)
        
        if instance:
            ldss_admin = admin.site._registry[LuckyDrawSnapshot]
            remaining_ids = ldss_admin._calculate_flashback_snapshot_remaining_candidate_ids(instance)
            # add instance's selected ids for selected
            for w in instance.current_winners.all():
                remaining_ids.add(w.id) 
            qs = Candidate.objects.filter(id__in=remaining_ids)
        else:
            qs = Candidate.objects.all()
            
        self.fields['current_winners'] = forms.ModelMultipleChoiceField(
                                            queryset=qs, 
                                            required=False,
                                            widget=FilteredSelectMultiple(
                                                verbose_name=_('Current Winners'),
                                                is_stacked=False
                                            ))
   
    class Meta:
        model = LuckyDrawSnapshot