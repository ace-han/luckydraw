from django import forms
from django.core.exceptions import ValidationError
from django.forms.util import ErrorDict
from django.utils.translation import ugettext_lazy as _
from slotmachine.staff.helpers import FileExtensionValidator
from slotmachine.staff.models import Candidate



class CandidateForm(forms.ModelForm):
    candidate_list = forms.FileField(help_text=_('When an excel file is uploaded, other info would be ignore.'),
                           validators=[FileExtensionValidator(exts=['.xls', '.xlsx']), ],
                           required=False)
    upload_field_name = 'candidate_list'
    
    def full_clean(self):
        """
        Cleans all of self.data and populates self._errors and
        self.cleaned_data.
        """
        self._errors = ErrorDict()
        if not self.is_bound: # Stop further processing.
            return
        self.cleaned_data = {}
        # If the form is permitted to be empty, and none of the form data has
        # changed from the initial data, short circuit any validation.
        if self.empty_permitted and not self.has_changed():
            return
        if self.upload_field_name in self.changed_data:
            self._clean_fields()
        else: 
            super(CandidateForm, self)._clean_fields()
            
        self._clean_form()
        
        if self.upload_field_name not in self.changed_data:
            self._post_clean()
        
        if self._errors:
            del self.cleaned_data
    
    def _clean_fields(self):
        '''
            only cater upload file field
        '''
        field = self.fields.get(self.upload_field_name)
        value = field.widget.value_from_datadict(self.data, self.files, self.add_prefix(self.upload_field_name))
        try:
            initial = self.initial.get(self.upload_field_name, field.initial)
            value = field.clean(value, initial)
            self.cleaned_data[self.upload_field_name] = value
            if hasattr(self, 'clean_%s' % self.upload_field_name):
                value = getattr(self, 'clean_%s' % self.upload_field_name)()
                self.cleaned_data[self.upload_field_name] = value
        except ValidationError, e:
            self._errors[self.upload_field_name] = self.error_class(e.messages)
            if self.upload_field_name in self.cleaned_data:
                del self.cleaned_data[self.upload_field_name]
    
    class Meta:
        model = Candidate