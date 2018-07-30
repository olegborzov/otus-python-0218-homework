from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter(is_safe=False)
@stringfilter
def pluralize(value, forms):
    """
    Подбирает окончание существительному после числа
    {{someval|pluralize:"товар,товара,товаров"}}
    """
    try:
        one, two, many = forms.split(u',')
        value = str(value)[-2:]  # 314 -> 14

        if 4 < int(value) < 21:
            return many

        if value.endswith('1'):
            return one
        elif value.endswith(('2', '3', '4')):
            return two
        else:
            return many

    except (ValueError, TypeError):
        return ''
