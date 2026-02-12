from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def url_replace(context, field, value):
    """Return encoded querystring with `field` set to `value`, preserving other GET params.

    If `value` is falsy (None, empty string, or literal 'None'), the parameter will be removed
    from the returned querystring. This makes it convenient to *toggle* flags while keeping
    other GET parameters intact.
    """
    request = context.get('request')
    if not request:
        return ''
    params = request.GET.copy()
    # Treat falsy values as removal requests so template toggles work as expected
    if value in (None, '', 'None'):
        params.pop(field, None)
    else:
        params[field] = value
    return params.urlencode()
