from django import template

register = template.Library()

@register.simple_tag
def mmr_to_rank(mmr, highest_mmr, lowest_mmr):
    if highest_mmr == lowest_mmr:
        return 'Stone', '#ffffff'

    # Calculate the percentile
    percentile = (highest_mmr - mmr) / (highest_mmr - lowest_mmr)

    # Determine rank based on percentile

    if percentile <= 0.08:
        return 'Untouchable', '#973df6'
    elif percentile <= 0.16:
        return 'Legend', '#be89f6'
    elif percentile <= 0.25:
        return 'Grandmaster', '#cb001c'
    elif percentile <= 0.33:
        return 'Master', '#d15858'
    elif percentile <= 0.41:
        return 'Challenger', '#f985cb'
    elif percentile <= 0.50:
        return 'Diamond', '#c6d2ff'
    elif percentile <= 0.58:
        return 'Platinum', '#0089a1'
    elif percentile <= 0.66:
        return 'Gold', '#ebce75'
    elif percentile <= 0.75:
        return 'Silver', '#d9d9d9'
    elif percentile <= 0.83:
        return 'Bronze', '#b8a25e'
    elif percentile <= 0.91:
        return 'Iron', '#ffffff'
    else:
        return 'Stone', '#000000'
