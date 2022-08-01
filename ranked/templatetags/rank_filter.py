from django import template

register = template.Library()

def mmr_to_rank(mmr):
    if mmr > 1600:
        return 'Challenger'
    elif mmr > 1500:
        return 'Grandmaster'
    elif mmr > 1400:
        return 'Master'
    elif mmr > 1300:
        return 'Diamond'
    elif mmr > 1200:
        return 'Platinum'
    elif mmr > 1100:
        return 'Gold'
    elif mmr > 1000:
        return 'Silver'
    elif mmr > 900:
        return 'Bronze'
    elif mmr > 800:
        return 'Iron'
    else:
        return 'Stone'

register.filter('get_rank', mmr_to_rank)