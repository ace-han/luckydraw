from django import template
from django.templatetags import static
import re

register = template.Library()

MIN_ENDING_PATTERN = re.compile(r'(?P<main>[\w\-\.\/]+)\.min(?P<suffix>\.\w+)$', re.I)

@register.simple_tag(takes_context=True)
def debug(context, path, switch_key='debug'):
    """
    return a xxx[.min].js, xxx[.min].css or anything whose pattern is xxx[.min].suffix 
        that goes with {% static %} share the same url
        
    
    ``settings.STATIC_URL``.

    Usage::
        {% debug "myapp/css/base.css" %}
        {% debug variable_with_path %}
        
    Examples::

        1. appending NOTHING to url {% debug xxx.suffix %} return 'xxx.suffix'
        2. appending NOTHING to url {% debug xxx.min.suffix %} return 'xxx.min.suffix'
        3. appending ?debug=true and {% debug "myapp/css/base.css" %} return "myapp/css/base.css"
        4. appending ?debug=true and {% debug "myapp/css/base.min.css" %} return "myapp/css/base.css"
        3. appending ?disable_min=true and {% debug "myapp/css/base.css" switch_key='disable_min' %} return "myapp/css/base.css"
        4. appending ?disable_min=true and {% debug "myapp/css/base.min.css" switch_key='disable_min' %} return "myapp/css/base.css"
        5. appending ?debug=true and {% debug "myapp/css/base.min.css" switch_key='disable_min' %} return "myapp/css/base.min.css"

        P.S.
            Case 1 and 2, just work like static 
    """
    actual_path = static.static(path)
    
    request = context.get('request', None)
    
    if request and bool(request.GET.get(switch_key)):
        actual_path = MIN_ENDING_PATTERN.sub('\g<main>\g<suffix>', actual_path)

    return actual_path