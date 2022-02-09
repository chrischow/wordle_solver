# *------------------*
# | GYX CALCULATIONS |
# *------------------*
import numpy as np
import pandas as pd

from . import get_feedback, init_vec, init_set, alpha_dict, encode_word
from joblib import Parallel, delayed
from tqdm.notebook import tqdm

# *------------*
# | GYX SCORES |
# *------------*
def get_gyx_scores_single(input_word, solution_set):
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


def get_gyx_scores_all(candidate_set, solution_set, parallel=True, n_jobs=-2,
                       backend='loky', verbose=True):
    '''
Computes the green/yellow/grey (GYX) scores for all candidates in the set
`candidate_set` against each of the words in a set of answers `solution_set`.

Returns a dataframe with:

1. The original candidate
2. The average number of green tiles hit
3. The average number of yellow tiles hit
4. The weighted average number of tiles hit: AVG = G * 2 + Y
5. The rank for green tiles hit
6. The rank for yellow tiles hit
7. The rank for the weight average
    '''

    if parallel:
        raw_scores = Parallel(n_jobs=n_jobs, backend=backend, verbose=int(verbose))(
            delayed(get_gyx_scores_single)(input_word, solution_set) \
                for input_word in tqdm(candidate_set.word, disable=not verbose)
        )

    else:
        raw_scores = []
        for input_word in tqdm(candidate_set.word, disable=not verbose):
            raw_scores.append(get_gyx_scores_single(input_word, solution_set))
    
    # Prepare dataframe
    df = pd.DataFrame(raw_scores, columns=['word', 'green_avg', 'yellow_avg', 'weighted_avg'])
    df['green_rank'] = df.green_avg.rank(ascending=False)
    df['yellow_rank'] = df.yellow_avg.rank(ascending=False)
    df['wt_avg_rank'] = df.weighted_avg.rank(ascending=False)
    df = df.sort_values('wt_avg_rank').reset_index(drop=True)

    return df

# *-------------------*
# | NO. OF CANDIDATES |
# *-------------------*
def compute_ncands_single(input_word, solution, wordset_vec):
    '''
Obtains the Wordle feedback from guessing a candidate `input_word` against
an answer `solution`, and uses that feedback to filter a given wordset `wordset`.
This checks how many feasible words would have remained in the set after filtering.

Returns a tuple with the candidate, the answer, the feedback, and the number
of words in the wordset after filtering.
    '''

    fb = get_feedback(input_word, solution)
    input_word_vec = encode_word(input_word)
    newset = wordset_vec.copy()
    for i, (letter, gyx) in enumerate(zip(input_word_vec, fb)):
        if gyx == 'G':
            newset = newset[newset[:, i] == letter]
        elif gyx == 'Y':
            newset = newset[np.logical_and(newset[:, 5+letter] > 0, newset[:, i] != letter)]
        else:
            newset = newset[newset[:, 5+letter] == 0]
    
    return input_word, solution, fb, newset.shape[0]


def compute_ncands_all(candidate_set, solution_set, wordset_vec, parallel=True,
                       n_jobs=-2, backend='loky', verbose=True):
    '''
Tests each candidate in the `candidate_set` against each solution in the
`solution_set` to check how many words would remain after filtering the
`wordset` using each feedback.

Returns a dataframe with:

1. Candidate word
2. Solution word
3. Feedback
4. No. of words remaining after filtering (`ncands`)
    '''
    if parallel:
        all_ncands = Parallel(n_jobs=n_jobs, backend=backend, verbose=int(verbose))(
            delayed(compute_ncands_single)(input_word, solution, wordset_vec) \
                for input_word in tqdm(candidate_set.word, disable=not verbose) \
                for solution in solution_set.word)
    else:
        all_ncands = []
        for input_word in tqdm(candidate_set.word, disable=not verbose):
            for solution in solution_set.word:
                all_ncands.append(
                    compute_ncands_single(input_word, solution, wordset_vec)
                )

    output = pd.DataFrame(all_ncands, columns=['word', 'solution',
                                               'fb', 'ncands'])

    return output

def summarise_ncands(df, by='ncands_max'):
    '''
Takes the output of `compute_ncands_all` (a dataframe) and summarises the
results based on the evaluated candidate `word`s. For sorting, choose either
`ncands_max` or `ncands_mean`. Returns a dataframe with:

1. Candidate
2. Max number of remaining candidates across a given solution set
3. Mean number of remaining candidates across a given solution set
    '''

    df = df.groupby('word').agg({
        'ncands': ['max', 'mean']
    }).reset_index()
    
    df.columns = ['word', 'ncands_max', 'ncands_mean']

    # Compute ranks
    df['ncands_max_rank'] = df.ncands_max.rank()
    df['ncands_mean_rank'] = df.ncands_mean.rank()
    df = df.sort_values(f'{by}_rank').reset_index(drop=True).head(10)

    return df

def entropy(x):
    '''
Computes the entropy of a given set of categories. Takes in a Pandas series
`x`, computes the relative frequencies, and then returns the entropy score.
    '''

    _, counts = np.unique(x, return_counts=True)
    probs = counts / np.sum(counts)
    return -np.sum(probs * np.log(probs))

def compute_fb_single(input_word, solution):
    fb = get_feedback(input_word, solution)
    return input_word, solution, fb

def compute_entropy_all(candidate_set, solution_set, parallel=True,
                        n_jobs=-2, backend='loky', verbose=True):
    if parallel:
        all_fb = Parallel(n_jobs=n_jobs, backend=backend, verbose=int(verbose))(
            delayed(compute_fb_single)(input_word, solution) \
                for input_word in tqdm(candidate_set.word, disable=not verbose) \
                for solution in solution_set.word
        )
    else:
        all_fb = []
        for input_word in tqdm(candidate_set.word, disable=not verbose):
            for solution in solution_set.word:
                all_fb.append(compute_fb_single(input_word, solution))
    
    output = pd.DataFrame(all_fb, columns=['word', 'solution', 'fb'])

    return output

def summarise_entropy(df):
    df = df.groupby('word').agg({
        'fb': [
            # ('nbuckets', pd.Series.nunique),
            ('fb_entropy', entropy)
        ]
    }).reset_index()
    
    df.columns = ['word', 'fb_entropy']

    df = df.sort_values('fb_entropy', ascending=False)
    return df

# *-----------------------------------------*
# | VECTORISED FUNCTIONS FOR GYX AND NCANDS |
# *-----------------------------------------*
# You might not want to use a vectorised approach. The additional computations
# from processing size (26, 5) vectors instead of 1x5 words is much larger.
def compute_cands(gyx_triplet, solutions_vector):
    
    gyx_triplet = gyx_triplet.reshape(3,26,5)
    
    # Green checks
    if np.sum(gyx_triplet[0]) > 0:
        green_boolean = np.sum(gyx_triplet[0] * solutions_vector == gyx_triplet[0], axis=(-2,-1)) == 130
        filtered_solutions = solutions_vector[green_boolean]
    else:
        filtered_solutions = solutions_vector.copy()
    
    # Yellow avoid: All yellow locations are zero
    if np.sum(gyx_triplet[1]) > 0:
        yellow_avoid = np.sum(gyx_triplet[1] * filtered_solutions == 0, axis=(-2,-1)) == 130

        # Yellow present: 
        # 1. Compute row sums for yellow vector
        # 2. Select rows with at least one yellow in each solution word vector
        # 3. Compute row sums for solution vector to check there are at least one
        # 4. Check that there are two
        yellow_sums = np.sum(gyx_triplet[1], axis=-1)
        yellow_present = np.sum(
            np.sum(filtered_solutions[:, yellow_sums >= 1, :], axis=-1) >= 1,
            axis=-1) == 2

        # Combine yellow checks
        yellow_boolean = yellow_present * yellow_avoid

        # Filter based on yellows
        filtered_solutions = filtered_solutions[yellow_boolean]

    # Grey checks
    if np.sum(gyx_triplet[2]) > 0:
        grey_boolean = np.sum(np.sum(gyx_triplet[2], axis=-1, keepdims=True) * filtered_solutions == 0, axis=(-2,-1)) == 130
        filtered_solutions = filtered_solutions[grey_boolean]

    # Count no. of candidates
    return filtered_solutions.shape[0]

def get_gyx_ncands_single(word, solutions_vector):
    '''
Takes a word, converts it into a 26x5 vector, and performs vectorised computations
for the following metrics for a given word vs. all solutions' vectors:

1. Greens/yellows/greys across all solutions
2. Average GYX score
3. Max no. of candidates
4. Mean no. of candidates

Returns a dictionary with these metrics.
    '''
    word_vec = init_vec(word)

    # Compute GYX scores
    greens = solutions_vector * word_vec
    yellows = word_vec * (
        (solutions_vector.sum(axis=2) >= word_vec.sum(axis=1)) & 
        (word_vec.sum(axis=1) > 0)) \
        .reshape(solutions_vector.shape[0], 26, 1) - greens
    greys = word_vec - greens - yellows
    scores = np.array([np.sum(greens, axis=(1,2)), np.sum(yellows, axis=(1,2)), np.sum(greys, axis=(1,2))]).T
    scores = scores.mean(axis=1)

    # Set up GYX tensor
    gyx_reshaped = np.stack([greens, yellows, greys], axis=1)
    gyx_reshaped = gyx_reshaped.reshape(solutions_vector.shape[0], 390)
    
    # Compute raw candidate data
    ncands = np.apply_along_axis(compute_cands, 1, gyx_reshaped, solutions_vector=solutions_vector)
    ncands_max = np.max(ncands)
    ncands_mean = np.mean(ncands)
        
    return {
        'word': word, 'g': scores[0], 'y': scores[1], 'x': scores[2],
        'gyx_score': scores[0] * 2 + scores[1],
        'ncands_max': ncands_max, 'ncands_mean': ncands_mean
    }


def get_gyx_ncands_all(candidate_set, solutions_vector, parallel=True):
    '''
Tests each candidate in the `candidate_set` against each solution in the
`solution_set`, and uses *each* feedback tensor to check how many words would
remain in the `solution_set` after filtering using each feedback.

Returns a dataframe with:

1. Candidate word
2. Average green tiles
3. Average yellow tiles
4. Average grey tiles
5. Weighted average GYX score
6. Max no. of candidates
7. Mean no. of candidates
    '''
    if parallel:
        all_data = Parallel(n_jobs=5, verbose=1)(
            delayed(get_gyx_ncands_single)(input_word, solutions_vector) \
                for input_word in tqdm(candidate_set.word))
    else:
        all_data = []
        for input_word in tqdm(candidate_set.word):
            all_data.append(get_gyx_ncands_single(input_word, solutions_vector))

    output = pd.DataFrame(all_data)

    return output