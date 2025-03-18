from django import template

register = template.Library()

@register.filter
def calc_percent(value, arg):
    try:
        return min((int(value) / int(arg)) * 100, 100)
    except (ValueError, ZeroDivisionError):
        return 0