# Win probability scaling divisor.
# Standard ELO uses 400; 256 makes the curve steeper (rating differences matter more).
N = 256

# Minimum ELO a player can reach.
ELO_FLOOR = 100

# Base K-factor by alliance size.
# Smaller teams = more individual control = faster ELO movement.
K_BY_SIZE = {1: 16, 2: 12, 3: 10}

# Score margin bonus weight by alliance size (0 to this many additional ELO points).
# In 1v1 you control the scoreline; in 3v3 a blowout reflects the team, not you individually.
SCORE_WEIGHT_BY_SIZE = {1: 4, 2: 3, 3: 2}

# New player experience multiplier.
# Starts at this value for 0-game players, decays toward 1.0 as games accumulate.
NEW_PLAYER_MULT = 3.0

# Characteristic game count for experience decay, by alliance size.
# Larger teams need more games to average out variance before ELO stabilises.
EXP_GAMES_BY_SIZE = {1: 30, 2: 40, 3: 50}
