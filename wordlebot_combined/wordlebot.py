# +-----------+
# | WORDLEBOT |
# +-----------+
import json
import numpy as np
import pandas as pd

from joblib import Parallel, delayed
from tqdm.notebook import tqdm

# *--------------*
# | PROCESS DATA |
# *--------------*
# Dictionary mapping letters to numbers
alpha_dict = {l: i for i, l in enumerate(list('abcdefghijklmnopqrstuvwxyz'))}

# Load data
def load_data(path):

    with open(f'{path}/wordle-candidates.json', 'r') as file:
        wordle_candidates = json.load(file)
        
    with open(f'{path}/wordle-answers.json', 'r') as file:
        wordle_answers = json.load(file)

    wordle_candidates = pd.DataFrame(wordle_candidates['words'], columns=['word'])
    wordle_answers = pd.DataFrame(wordle_answers['words'], columns=['word'])

    # Extract letters
    for i in range(5):
        wordle_candidates[f'p{i}'] = wordle_candidates.word.str[i]
        wordle_answers[f'p{i}'] = wordle_answers.word.str[i]

    for l in list('abcdefghijklmnopqrstuvwxyz'):
        wordle_candidates[f'letter_{l}'] = wordle_candidates.word.apply(lambda x: x.count(l))
        wordle_answers[f'letter_{l}'] = wordle_answers.word.apply(lambda x: x.count(l))

    wordle = wordle_candidates.loc[
        wordle_candidates.word.apply(lambda x: len(x)==len(set(x)))
    ].append(wordle_answers).reset_index(drop=True)

    return wordle_candidates, wordle_answers

# *------------*
# | GAME LOGIC |
# *------------*
def get_feedback(input_word, solution):
    '''
    Takes an `input_word` and `solution`, and returns Wordle feedback in the
    form: [G|Y|X] * 6. G = green, Y = yellow, X = grey.
    '''
    output = ''
    for i in range(5):
        if input_word[i] == solution[i]:
            output += 'G'
        elif input_word[i] in solution:
            output += 'Y'
        else:
            output += 'X'
    return output

def filter_wordset(input_word, feedback, wordset):
    '''
    Uses an input word and feedback to filter a wordset.
    '''
    newset = wordset.copy()
    for i, (letter, gyx) in enumerate(zip(input_word, feedback)):
        if gyx == 'G':
            newset = newset.loc[newset[f'p{i}'] == letter]
        elif gyx == 'Y':
            newset = newset.loc[newset[f'letter_{letter}'].gt(0) & newset[f'p{i}'].ne(letter)]
        else:
            newset = newset.loc[newset[f'letter_{letter}'].eq(0)]
    
    return newset


def filter_candidates(candidate_set, solution_set):
    '''
    Analyses the letters at each position in a solution set, and removes \
    candidates
    '''
    unique_sums = np.zeros(candidate_set.word.shape)

    # Check unique letters
    for i in range(5):
        unique_letters = solution_set[f'p{i}'].unique()
        unique_sums = unique_sums + candidate_set[f'p{i}'].isin(unique_letters).astype(int).values

    return candidate_set.loc[pd.Series(unique_sums).gt(0).values]

# *---------------*
# | VECTORISATION |
# *---------------*
def init_set(wordset):
    '''
Initialises a `n_samples` x 26 x 5 Numpy array for a given wordset.
    '''
    output = np.zeros((wordset.shape[0], 26, 5), dtype='int8')
    for i, word in enumerate(wordset.word):
        for j, l in enumerate(word):
            output[i, alpha_dict[l], j] = 1
    return output

def init_vec(word):
    '''
Initialises a 26 x 5 Numpy array for a given word.
    '''
    mat = np.zeros((26, 5), dtype='int8')
    for i, l in enumerate(word):
        mat[alpha_dict[l], i] = 1
    return mat

def encode_word(word):
    '''Convert word into a 1D array of 8-bit integers.
    '''
    return np.array([alpha_dict[x] for x in word], dtype='int8')

def encode_set(wordset):
    '''
Convert wordset into a 2D array with 5 columns representing each letter of each
word, and an additional 26 columns holding counts of each of the 26 letters of
the alphabet in that word.
    '''
    wordset_np = np.zeros((wordset.shape[0], 5), dtype='int8')
    for i in range(5):
        wordset_np[:, i] = wordset[f'p{i}'].apply(lambda x: alpha_dict[x])

    for l in list('abcdefghijklmnopqrstuvwxyz'):
        wordset_np = np.hstack([
            wordset_np,
            np.sum(wordset_np[:, :5] == alpha_dict[l], axis=1, keepdims=True)
        ]).astype('int8')
    
    return wordset_np

# *------------*
# | GAME CLASS |
# *------------*
from wordlebot.gyx import get_gyx_scores_all, compute_ncands_all, summarise_ncands
from wordlebot.lf import compute_letter_frequencies, compute_lf_score

class Wordle():
    def __init__(self, candidates, solutions, solution=None, verbose=True):
        self.guesses = []
        self.feedback = []
        self.ncands = []
        self.candidates = candidates
        self.solutions = solutions
        self.optimisations = {}
        self.last_optimised = {'ncands': -1, 'lf': -1, 'expected_gyx': -1}
        self.step = 0
        self.solved = False
        self.verbose = verbose
        
        if solution:
            self.solution = solution
        else:
            self.solution = None
    
    def reset(self, solution=None):
        self.guesses = []
        self.feedback = []
        self.ncands = []
        self.candidates = candidates
        self.solutions = solutions
        self.optimisations = {}
        self.last_optimised = {'ncands': -1, 'lf': -1, 'expected_gyx': -1}
        self.step = 0
        self.solved = False
        self.verbose = verbose
        
        if solution:
            self.solution = solution
        else:
            self.solution = None
            
    def guess(self, guess, feedback=None):
        if self.solved:
            if self.verbose:
                print('Game already solved.')
            return
        
        if self.solution:
            feedback = get_feedback(guess, self.solution)
        else:
            # Check entry
            if not feedback:
                raise ValueError('Please input feedback.')
            if any([not letter in ['x', 'y', 'g'] for letter in feedback]):
                raise ValueError('Please input G, Y, or X only.')
        
        if feedback != 'GGGGG':
            # Update solutions
            self.solutions = filter_wordset(guess, feedback.upper(), self.solutions)
            
            # Update candidates
            self.candidates = filter_candidates(self.candidates, self.solutions)

        if self.verbose:
            print(f'{guess.upper()} --> {feedback.upper()}: {self.solutions.shape[0]} solutions remaining.')

        # Save data
        self.guesses.append(guess.lower())
        self.feedback.append(feedback.upper())
        self.ncands.append(self.solutions.shape[0])
        self.step += 1
        
        if feedback == 'GGGGG':
            self.solved = True
            if self.verbose:
                self.status()

        # Autosolve
        if self.solutions.shape[0] == 1 and feedback != 'GGGGG':
            self.solved = True
            self.step += 1
            if len(self.guesses) < self.step:
                self.guesses.append(self.solutions.word.tolist()[0])
            if len(self.feedback) < self.step:
                self.feedback.append('GGGGG')
            if len(self.ncands) < self.step:
                self.ncands.append(1)
            if self.verbose:
                print(f'Game autosolved. Last guess: {self.solutions.word.tolist()[0].upper()}')
                self.status()
        
    def status(self):
        if self.verbose:
            output = pd.DataFrame({
                'word': self.guesses,
                'feedback': self.feedback,
                'n_candidates': self.ncands
            })
            if not self.solved:
                print(f'{self.solutions.shape[0]} solutions remaining.')
                print(f'{self.candidates.shape[0]} candidates remaining.\n')
            else:
                print(f'Game solved in {self.step} steps.')
            if output.shape[0] > 0:
                display(output)
            else:
                print('No data to display.')
        
    def optimise(self, method='ncands'):
        if not method in ['ncands', 'lf', 'expected_gyx']:
            raise ValueError('Please choose `ncands`, `lf`, or `expected_gyx`.')
        
        if self.solved:
            if self.verbose:
                print('Game already solved.')
            return
        
        if self.last_optimised[method] == self.step:
            return self.optimisations[method]
        
        if self.solutions.shape[0] <= 20:
            candidates = self.candidates.loc[self.candidates.word.isin(self.solutions.word)]
        else:
            candidates = self.candidates
        
        if method == 'ncands':
            # Initialise solutions numpy array
            solutions_vector = encode_set(self.solutions)
            
            df_scores = compute_ncands_all(candidates, self.solutions, solutions_vector, verbose=self.verbose)
            df = summarise_ncands(df_scores)

        elif method == 'expected_gyx':
            # Compute scores
            df = get_gyx_scores_all(candidates, self.solutions, verbose=self.verbose)
            
        elif method == 'lf':
            # Compute scores
            lf_freqs = compute_letter_frequencies(self.solutions).sum().to_dict()
            df = pd.DataFrame({'word': candidates.word,
                               'letter_freq': candidates.word.apply(compute_lf_score, freqs=lf_freqs)})
            df = df.sort_values('letter_freq', ascending=False).reset_index(drop=True)
        
        # Few solutions left: use popularity
        # if method != 'lf' and self.solutions.shape[0] <= 10:
        
        # Cache
        self.optimisations[method] = df
        self.last_optimised[method] = self.step
        return df

    def records(self):
        return {
            'steps': self.step,
            'words': self.guesses,
            'feedback': self.feedback,
            'ncands': self.ncands
        }

# *------------------*
# | GYX CALCULATIONS |
# *------------------*

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


def get_gyx_scores_all(candidate_set, solution_set, parallel=True):
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
        raw_scores = Parallel(n_jobs=3, verbose=int(verbose))(
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


def compute_ncands_all(candidate_set, solution_set, wordset_vec, parallel=True, verbose=True):
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
        all_ncands = Parallel(n_jobs=3, verbose=int(verbose))(
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

def entropy(x):
    '''
Computes the entropy of a given set of categories. Takes in a Pandas series
`x`, computes the relative frequencies, and then returns the entropy score.
    '''

    _, counts = np.unique(x, return_counts=True)
    probs = counts / np.sum(counts)
    return -np.sum(probs * np.log(probs))


def summarise_ncands(df):
    '''
Takes the output of `compute_ncands_all` (a dataframe) and summarises the
results based on the evaluated candidate `word`s. Returns a dataframe with:

1. Candidate
2. Max number of remaining candidates across a given solution set
3. Mean number of remaining candidates across a given solution set
4. Number of buckets (based on feedback) that remaining candidates are
    divided into
5. Entropy across the abovementioned buckets
    '''

    df = df.groupby('word').agg({
        'ncands': ['max', 'mean'],
        'fb': [('nbuckets', pd.Series.nunique),
               ('bucket_entropy', entropy)]
    }).reset_index()
    
    df.columns = ['word', 'ncands_max', 'ncands_mean', 'nbuckets', 'bucket_entropy']

    # Compute ranks
    df['ncands_max_rank'] = df.ncands_max.rank()
    df['ncands_mean_rank'] = df.ncands_mean.rank()
    df['bucket_entropy_rank'] = df.bucket_entropy.rank(ascending=False)
    df['avg_rank'] = df[['ncands_max_rank', 'bucket_entropy_rank']].mean(axis=1)
    df = df.sort_values('avg_rank').reset_index(drop=True).head(10)

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
        all_data = Parallel(n_jobs=3, verbose=1)(
            delayed(get_gyx_ncands_single)(input_word, solutions_vector) \
                for input_word in tqdm(candidate_set.word))
    else:
        all_data = []
        for input_word in tqdm(candidate_set.word):
            all_data.append(get_gyx_ncands_single(input_word, solutions_vector))

    output = pd.DataFrame(all_data)

    return output


# *--------------------*
# | LETTER FREQUENCIES |
# *--------------------*

def compute_letter_frequencies(wordset):
    '''
    Creates a dictionary with letter frequencies. Letters are stored as keys,
    and their respective counts are in the values.
    '''
    w = wordset.copy()
    for letter in list('abcdefghijklmnopqrstuvwxyz'):
        w[letter] = w.word.str.contains(letter).astype(int)
    return w.iloc[:, -26:]

def compute_lf_score(x, freqs):
    '''
    Computes the score for a word `x`, given the letter frequencies dictionary
    `freqs`, computed using the `compute_letter_frequencies(wordset)` function.
    '''
    letters = set(x)
    output = 0
    for letter in letters:
        output += freqs[letter]
    return output