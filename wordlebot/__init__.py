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

def load_word_popularity(path):
    word_popularity = pd.read_table(f'{path}/en_words_1_5-5.txt', delimiter=' ', header=None, index_col=None,
                                    names=['word_len', 'word_freq', 'n_articles']).reset_index()
    word_popularity = word_popularity.rename(columns={'index': 'word'})

    # Filter by english
    alphabet = list('abcdefghijklmnopqrstuvwxyz')
    word_popularity = word_popularity.loc[
        word_popularity.word.apply(lambda x: all([l in alphabet for l in x]))] \
            .reset_index(drop=True)
    return word_popularity

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

            # Fix for infinite loops
            self.solutions = self.solutions.loc[~self.solutions.word.isin(self.guesses)]
            self.candidates = self.candidates.loc[~self.candidates.word.isin(self.guesses)]
            
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
        
    def optimise(self, method='ncands', n_jobs=-2, backend='loky', by='bucket_entropy'):
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
            
            df_scores = compute_ncands_all(candidate_set=candidates,
                                           solution_set=self.solutions,
                                           wordset_vec=solutions_vector,
                                           n_jobs=n_jobs, backend=backend,
                                           verbose=self.verbose)
            df = summarise_ncands(df_scores, by=by)

        elif method == 'expected_gyx':
            # Compute scores
            df = get_gyx_scores_all(candidate_set=candidates, solution_set=self.solutions,
                                    n_jobs=n_jobs, backend=backend, verbose=self.verbose)
            
        elif method == 'lf':
            # Compute scores
            lf_freqs = compute_letter_frequencies(self.solutions).sum().to_dict()
            df = pd.DataFrame({'word': candidates.word,
                               'letter_freq': candidates.word.apply(compute_lf_score, freqs=lf_freqs)})
            df = df.sort_values('letter_freq', ascending=False).reset_index(drop=True)
        
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

    def reprioritise(self, plugin='popularity', data=None):
        if plugin == 'popularity':
            df = self.solutions.merge(
                data[['word', 'word_freq', 'n_articles']],
                how='left', left_on='word', right_on='word')
            
            df = df.sort_values('word_freq', ascending=False)
            return df[['word', 'word_freq', 'n_articles']]
        elif plugin == 'splitter':
            
            # Copy data
            wc = self.candidates.copy()
            df = self.solutions.copy()

            # Extract letters
            for i in range(5):
                df[f'p{i}'] = df.word.str[i]
                wc[f'p{i}'] = wc.word.str[i]

            # Count number of unique columns
            unique_mask = df[[f'p{i}' for i in range(5)]].nunique() > 1
            cols = unique_mask.index[unique_mask]

            # 1 unique column only
            if unique_mask.sum() == 1:    
                total_letters = df.shape[0]
                wc['scores'] = 0
                wc['counts'] = 0
                
                # Get unique letters
                unique_letters = np.unique(np.squeeze(df[cols].values))
                for i, letter in enumerate(unique_letters):
                    contains_letter = wc[cols[0]].eq(letter).astype(int)
                    # Apply highest weight 
                    wc['scores'] = wc['scores'] + (total_letters - i) * contains_letter
                    wc['counts'] = wc['counts'] + contains_letter

                wc = wc.sort_values('scores', ascending=False).reset_index(drop=True)
                return wc

            elif unique_mask.sum() == 2:
                from collections import Counter
                wc['scores'] = 0
                for col in cols:
                    counter = Counter(df[col])
                    temp_scores = pd.to_numeric(wc[col].replace(counter), errors='coerce').fillna(0) 
                    wc['scores'] = wc['scores'] + temp_scores
                
                wc = wc.sort_values('scores', ascending=False).reset_index(drop=True)
                return wc
