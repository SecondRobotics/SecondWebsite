from django import template

register = template.Library()

@register.simple_tag
def mmr_to_rank(mmr, highest_mmr, lowest_mmr):
    if highest_mmr == lowest_mmr:
        return 'Stone'  # All players have the same MMR, edge case

    # Calculate the percentile
    percentile = (highest_mmr - mmr) / (highest_mmr - lowest_mmr)
    
    # Determine rank based on percentile
    if percentile <= 0.1:
        return 'Challenger'
    elif percentile <= 0.2:
        return 'Grandmaster'
    elif percentile <= 0.3:
        return 'Master'
    elif percentile <= 0.4:
        return 'Diamond'
    elif percentile <= 0.5:
        return 'Platinum'
    elif percentile <= 0.6:
        return 'Gold'
    elif percentile <= 0.7:
        return 'Silver'
    elif percentile <= 0.8:
        return 'Bronze'
    elif percentile <= 0.9:
        return 'Iron'
    else:
        return 'Stone'
