# +-----------+
# | WORDLEBOT |
# +-----------+
import json
import numpy as np
import pandas as pd

from joblib import Parallel, delayed
from tqdm.notebook import tqdm


# *--------------*
# | EXPECTED GYX |
# *--------------*
def get_gyx_scores(input_word, solution_set):
    '''
    Computes the green/yellow/grey (GYX) scores by comparing a candidate
    `input_word` against each of the words in a set of answers `solution_set`.
    
    Returns:
        1. The original candidate
        2. The average number of green tiles hit
        3. The average number of yellow tiles hit
        4. The weighted average number of tiles hit: AVG = G * 2 + Y
    '''
    feedback = solution_set.word.apply(lambda x: get_feedback(input_word, x))
    greens = feedback.apply(lambda x: x.count('G'))
    yellows = feedback.apply(lambda x: x.count('Y'))
    green_avg = greens.mean()
    yellow_avg = yellows.mean()
    weighted_avg = np.mean(greens * 3 + yellows)

    return input_word, green_avg, yellow_avg, weighted_avg


