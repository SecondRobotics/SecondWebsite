from django import template

register = template.Library()

@register.simple_tag
def mmr_to_rank(mmr, highest_mmr, lowest_mmr):
    if highest_mmr == lowest_mmr:
        return 'Stone', '#ffffff'

    # Calculate the percentile
    percentile = (highest_mmr - mmr) / (highest_mmr - lowest_mmr)

    # Determine rank based on percentile
    if percentile <= 0.1:
        return 'Challenger', '#ffffff'
    elif percentile <= 0.2:
        return 'Grandmaster', '#ffffff'
    elif percentile <= 0.3:
        return 'Master', '#ffffff'
    elif percentile <= 0.4:
        return 'Diamond', '#ffffff'
    elif percentile <= 0.5:
        return 'Platinum', '#ffffff'
    elif percentile <= 0.6:
        return 'Gold', '#ebce75'
    elif percentile <= 0.7:
        return 'Silver', '#ffffff'
    elif percentile <= 0.8:
        return 'Bronze', '#ffffff'
    elif percentile <= 0.9:
        return 'Iron', '#ffffff'
    else:
        return 'Stone', '#ffffff'
