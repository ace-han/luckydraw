from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db.models.query import QuerySet
from django.utils.simplejson.encoder import JSONEncoder
from django.utils.translation import ugettext_lazy as _
from slotmachine.staff.models import Candidate
import mimetypes

class CandidateJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, QuerySet) \
        and obj.model == Candidate:
            result = [];
            for c in obj:
                result.append(self.__construct_simple_candidate(c))
            return result
        elif isinstance(obj, Candidate):
            return self.__construct_simple_candidate(obj)
        else: 
            return JSONEncoder.default(self,obj)
    
    def __construct_simple_candidate(self, candidate):
        return {'id': candidate.serializable_value('id')
               , 'en_name': candidate.serializable_value('en_name')
               , 'zh_name': candidate.serializable_value('zh_name')
               , 'department': candidate.serializable_value('department')};
               
# if needed we would extract this to a single file
class FileExtensionValidator(object):
    exts = []   # eg: ['.xls', '.xlsx', ...] with a leading dot(.)
    message = _(u'File Extension as %(file_ext)s won\'t be acceptable. Only %(exts)s will do')
    code = 'ext-invalid'
    
    def __init__(self, exts=[], message=None, code=None):
        if message:
            self.message = message
        if code:
            self.code = code

        if not exts:
            raise ImproperlyConfigured(_('Acceptable extensions should be provided'))
        
        for ext in exts:
            type, encoding = mimetypes.guess_type('a' + ext)
            if type:
                self.exts.append(ext)

    def __call__(self, value):
        """
        Validates that the file extension whether acceptable or not.
        usually use for upload file scenario
        """
        type, encoding = mimetypes.guess_type(value.name)
        exts = mimetypes.guess_all_extensions(type)
        for ext in exts:
            for e in self.exts:
                if e == ext:
                    return
        raise ValidationError(self.message % {'file_ext': ', '.join(exts), 
                                              'exts': ', '.join(self.exts)}, 
                                  code=self.code)