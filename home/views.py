from ranked.models import PlayerElo, GameMode
from .models import HistoricEvent, Staff
from django.http.response import HttpResponseRedirect
from discordoauth2.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib import messages
from .forms import ProfileForm
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _

from highscores.models import CleanCodeSubmission, Score, Leaderboard
from django.db.models import OuterRef, Subquery, Exists, Max


def index(response):
    return render(response, "home/home.html", {})


def about(response):
    return render(response, "home/about.html", {})


def mrc(response):
    return render(response, "home/mrc.html", {})


def rules(response):
    return render(response, "home/rules.html", {})


def staff(response):
    staff = Staff.objects.all()
    return render(response, "home/staff.html", {"staffs": staff})


def privacy(response):
    return render(response, "home/privacy.html", {})


def src_rules(_response):
    return redirect('https://bit.ly/SRCrules')


def stc_rules(_response):
    return redirect('https://bit.ly/STC-rules')


def mrc_rules(_response):
    return redirect('https://bit.ly/MRC-rules')


def svc_rules(_response):
    return redirect('https://bit.ly/SVCrules')


def discord(_response):
    return redirect('https://www.discord.gg/Zq3HXRc')


def merch(_response):
    return redirect('https://store.secondrobotics.org/')


def hall_of_fame(response):
    events = HistoricEvent.objects.all().order_by('-date')
    return render(response, "home/hall_of_fame.html", {"events": events})


def logos(response):
    return render(response, "home/logos.html", {})


def link_success(response):
    return render(response, "home/link_success.html", {})


def login_page(request):
    if request.user.is_authenticated:
        return redirect('/')
    else:
        return redirect('/oauth2/login')


def login_error(request):
    return render(request, "home/login_error.html", {})


def logout_user(request):
    logout(request)
    return redirect('/')


def reauth_user(request):
    logout(request)
    return redirect('/oauth2/login')


def user_profile(request, user_id: int):
    try:
        user = User.objects.get(id=user_id)
    except (User.DoesNotExist, OverflowError):
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    # Filter out test game/leaderboards
    all_leaderboards = Leaderboard.objects.exclude(game__icontains='test')
    scores = Score.objects.filter(player=user, approved=True).order_by('-time_set')

    # Calculate additional stats
    world_records = 0
    total_scores = 0
    total_percentile = 0
    recent_scores = scores[:5]  # Last 5 scores for recent activity

    games = {}
    for leaderboard in all_leaderboards:
        game_name = leaderboard.game
        if game_name not in games:
            games[game_name] = {
                "slug": leaderboard.game_slug,
                "leaderboards": [],
                "overall": 0,
                "robots_with_scores": 0,
                "total_percentile": 0
            }
        
        user_score = scores.filter(leaderboard=leaderboard).first()
        score_value = user_score.score if user_score else 0
        games[game_name]["overall"] += score_value

        # Calculate percentile and check for world records
        if user_score:
            highest_score = Score.objects.filter(leaderboard=leaderboard, approved=True).aggregate(Max('score'))['score__max']
            percentile = (score_value / highest_score) * 100 if highest_score else 0
            games[game_name]["robots_with_scores"] += 1
            games[game_name]["total_percentile"] += percentile
            
            # Track world records and overall stats
            if score_value == highest_score and highest_score > 0:
                world_records += 1
            total_scores += 1
            total_percentile += percentile
        else:
            percentile = 0

        games[game_name]["leaderboards"].append({
            "leaderboard": leaderboard,
            "score": score_value,
            "percentile": percentile,
            "source": user_score.source if user_score else None,
            "time_set": user_score.time_set if user_score else None
        })

    # Sort leaderboards within each game by percentile (highest to lowest)
    for game_name in games:
        games[game_name]["leaderboards"].sort(key=lambda x: x["percentile"], reverse=True)
        
        # Calculate average percentiles - include all robots (missing ones count as 0%)
        total_robots = len(games[game_name]["leaderboards"])
        if total_robots > 0:
            games[game_name]["avg_percentile"] = games[game_name]["total_percentile"] / total_robots
        else:
            games[game_name]["avg_percentile"] = 0

    # Filter out test game modes
    all_game_modes = GameMode.objects.exclude(game__icontains='test')
    player_elos = PlayerElo.objects.filter(player=user)
    
    elos_by_game = {}
    total_matches = 0
    
    # Group game modes by game and calculate stats
    ranked_games_stats = {}
    for game_mode in all_game_modes:
        elo_record = player_elos.filter(game_mode=game_mode).first()
        elos_by_game[game_mode] = elo_record
        if elo_record:
            total_matches += elo_record.matches_won + elo_record.matches_lost + elo_record.matches_drawn
        
        # Track stats per game
        game_name = game_mode.game
        if game_name not in ranked_games_stats:
            ranked_games_stats[game_name] = {
                'total_modes': 0,
                'modes_with_elo': 0,
                'total_elo': 0,
                'average_elo': 1200
            }
        ranked_games_stats[game_name]['total_modes'] += 1
        if elo_record:
            ranked_games_stats[game_name]['modes_with_elo'] += 1
            ranked_games_stats[game_name]['total_elo'] += elo_record.elo
        else:
            # Count missing ELOs as 1200
            ranked_games_stats[game_name]['total_elo'] += 1200

    # Calculate average ELOs
    for game_name in ranked_games_stats:
        stats = ranked_games_stats[game_name]
        if stats['total_modes'] > 0:
            stats['average_elo'] = round(stats['total_elo'] / stats['total_modes'], 0)
        else:
            stats['average_elo'] = 1200

    # Sort games by average percentile (highest to lowest)
    sorted_games = dict(sorted(games.items(), key=lambda item: item[1]["avg_percentile"], reverse=True))
    
    # Sort elos_by_game by average ELO (highest to lowest)
    sorted_elos_by_game = dict(sorted(
        elos_by_game.items(), 
        key=lambda item: ranked_games_stats.get(item[0].game, {}).get('average_elo', 1200),
        reverse=True
    ))
    
    # Calculate average performance
    avg_performance = (total_percentile / total_scores) if total_scores > 0 else 0
    
    context = {
        "games": sorted_games,
        "user": user,
        "elos_by_game": sorted_elos_by_game,
        "total_matches": total_matches,
        "ranked_games_stats": ranked_games_stats,
        "world_records": world_records,
        "total_scores": total_scores,
        "avg_performance": avg_performance,
        "recent_scores": recent_scores
    }
    return render(request, "home/user_profile.html", context)


@login_required(login_url='/login')
def merge_legacy_account(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = User.objects.filter(username=username)
        if user.exists():
            user = user[0]

            if password and len(password) > 3 and user.check_password(password) and user.is_active:
                # Copy attributes from old user to new user
                for score in Score.objects.filter(player=user):
                    score.player = request.user
                    score.save()
                for score in CleanCodeSubmission.objects.filter(player=user):
                    score.player = request.user
                    score.save()

                request.user.date_joined = user.date_joined
                request.user.save()

                # Deactivate old user
                user.is_superuser = False
                user.is_staff = False
                user.is_active = False
                user.save()

                return redirect('/user/%s' % request.user.id)

        messages.error(request, _("Username or password is incorrect!"))

    return render(request, "home/legacy_login.html", context={})


@login_required(login_url='/login')
def user_settings(request):
    user = request.user

    if request.method == "POST":
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Display name saved successfully."))
        else:
            messages.error(request, _("Enter a valid display name! This value may contain only English letters, "
                                      "numbers, and @/./+/-/_ characters. Must be between 4-25 characters."))
            return redirect('/user/settings')

    return render(request, "home/user_settings.html", context={})
