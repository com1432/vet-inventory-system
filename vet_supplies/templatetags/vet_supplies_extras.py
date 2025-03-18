from django import template

register = template.Library()

@register.filter
def calc_percent(value, arg):
    try:
        return min((int(value) / int(arg)) * 100, 100)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def days_percentage(timeuntil_str, max_days):
    try:
        if 'day' not in timeuntil_str:
            return 100
        days = int(timeuntil_str.split()[0])
        percentage = (days / max_days) * 100
        return min(100, percentage)
    except (ValueError, TypeError, IndexError):
        return 0