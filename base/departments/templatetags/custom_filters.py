from django import template

register = template.Library()

@register.filter
def last_category(value):
    if not value:
        return ''
    if '->' in str(value):
        return str(value).split('->')[-1].strip()
    else:
        return str(value).split('] ')[1]
