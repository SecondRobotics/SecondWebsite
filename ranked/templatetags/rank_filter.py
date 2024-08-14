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
        return 'Challenger', '#c7ffff'
    elif percentile <= 0.2:
        return 'Grandmaster', '#eb8686'
    elif percentile <= 0.3:
        return 'Master', '#f985cb'
    elif percentile <= 0.4:
        return 'Diamond', '#c6d2ff'
    elif percentile <= 0.5:
        return 'Platinum', '#54eac1'
    elif percentile <= 0.6:
        return 'Gold', '#ebce75'
    elif percentile <= 0.7:
        return 'Silver', '#d9d9d9'
    elif percentile <= 0.8:
        return 'Bronze', '#b8a25e'
    elif percentile <= 0.9:
        return 'Iron', '#ffffff'
    else:
        return 'Stone', '#000000'
