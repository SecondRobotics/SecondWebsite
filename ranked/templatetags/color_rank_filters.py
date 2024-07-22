from django import template

register = template.Library()

@register.filter(name='rank_color')
def rank_color(rank):
    colors = {
        'Gold': '#ebce75',
        # Add more rank-color mappings here if needed
    }
    return colors.get(rank, 'inherit')  # Default to 'inherit' if rank is not in the dictionary
