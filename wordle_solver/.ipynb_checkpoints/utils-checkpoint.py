import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from joblib import Parallel, delayed

sns.set()
P = '#7B73F0'
G = '#27DDCB'


# ---- GAME LOGIC ---- #
def get_feedback(input_word, solution):
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
    newset = wordset.copy()
    for i in range(5):
        if feedback[i] == 'G':
            newset = newset.loc[newset.word.str[i] == input_word[i]]
        elif feedback[i] == 'Y':
            # newset = newset.loc[newset.word.str.contains(input_word[i])]
            newset = newset.loc[newset.word.str.contains(input_word[i]) & newset.word.apply(lambda x: x[i] != input_word[i])]
        else:
            newset = newset.loc[~newset.word.str.contains(input_word[i])]
    return newset


# ---- SIMULATIONS ---- #
def sim_single(input_word, solution, score_fn, wordset=wordle):
    feedback = ''
    tested_words = []
    n_iter = 1

    while feedback != 'GGGGG':

        # Check solution
        feedback = get_feedback(input_word, solution)
        tested_words.append(input_word)
        
        # Filter wordset
        wordset = filter_wordset(input_word, feedback, wordset)
        wordset = wordset.loc[~wordset.word.isin(tested_words)]
        if n_iter == 1:
            first_cut = wordset.shape[0]
            second_cut = 0
        elif n_iter == 2:
            second_cut = wordset.shape[0]
            
        # Compute scores
        scores = score_fn(wordset)

        # Set new input word
        if scores.shape[0] > 0:
            input_word = scores.word.iloc[0]
            n_iter += 1
    return n_iter, first_cut, second_cut


def sim_double(input_word1, input_word2, solution, score_fn, wordset=wordle):
    feedback = ''
    tested_words = []
    n_iter = 1
    
    input_word = input_word1

    while feedback != 'GGGGG':

        # Check solution
        feedback = get_feedback(input_word, solution)
        tested_words.append(input_word)

        # Filter wordset
        wordset = filter_wordset(input_word, feedback, wordset)
        wordset = wordset.loc[~wordset.word.isin(tested_words)]
        if n_iter == 1:
            first_cut = wordset.shape[0]
            second_cut = 0
        elif n_iter == 2:
            second_cut = wordset.shape[0]

        # Compute scores
        scores = score_fn(wordset)

        # Set new input word
        if scores.shape[0] > 0:
            if len(tested_words) < 2:
                input_word = input_word2
            else:
                input_word = scores.word.iloc[0]
            n_iter += 1
    return n_iter, first_cut, second_cut


def run_sim(input_word, sim, score_fn, wordset=wordle, single=True, input_word2=None):
    
    if single:
        results = Parallel(n_jobs=5, verbose=3)(delayed(sim)(input_word, s, score_fn, wordset=wordset) for s in wordle_answers.word)
    else:
        assert input_word2 is not None
        results = Parallel(n_jobs=5, verbose=3)(delayed(sim)(input_word, input_word2, s, score_fn, wordset=wordset) for s in wordle_answers.word)
        
    data = pd.DataFrame(results, columns=['n_iter', 'first_cut', 'second_cut'])
    
    # Compute summary for no. of iterations
    summary_iter = pd.DataFrame(data.n_iter.describe()).T.reset_index(drop=True)
    summary_iter.columns = 'n_iter_' + summary_iter.columns
    summary_iter['iter_2_or_less'] = np.mean(data.n_iter <= 2)
    summary_iter['iter_3'] = np.mean(data.n_iter == 3)
    summary_iter['iter_4'] = np.mean(data.n_iter == 4)
    summary_iter['iter_5'] = np.mean(data.n_iter == 5)
    summary_iter['iter_6'] = np.mean(data.n_iter == 6)
    summary_iter['fail'] = np.mean(data.n_iter > 6)
    
    # Compute summary for first cut
    summary_c1 = pd.DataFrame(data.first_cut.describe()).T.reset_index(drop=True)
    summary_c1 = summary_c1.drop('count', axis=1)
    summary_c1.columns = 'c1_' + summary_c1.columns
    
    # Compute summary for second cut
    summary_c2 = pd.DataFrame(data.second_cut.describe()).T.reset_index(drop=True)
    summary_c2 = summary_c2.drop('count', axis=1)
    summary_c2.columns = 'c2_' + summary_c2.columns
    
    # Combine summary
    summary = pd.concat([summary_iter, summary_c1, summary_c2], axis=1)
    display(summary)
    if single:
        summary.insert(0, 'word', input_word)
        data.insert(0, 'word', input_word)
    else:
        summary.insert(0, 'words', f'{input_word}, {input_word2}')
        summary.insert(1, 'word1', input_word)
        summary.insert(2, 'word2', input_word2)
        data.insert(0, 'words', f'{input_word}, {input_word2}')
        data.insert(1, 'word1', input_word)
        data.insert(2, 'word2', input_word2)
        
    return summary, data


def eval_results(df, single=True):
    main_cols = ['n_iter_mean', 'c1_50%', 'c2_50%', 'iter_2_or_less',
               'iter_3', 'iter_4', 'iter_5', 'iter_6',
               'fail' ]
    if single:
        cols = ['word'] + main_cols
        yval = 'word'
    else:
        cols = ['words'] + main_cols
        yval = 'words'
        
    summary = df[cols].sort_values('n_iter_mean')
    display(summary)

    metrics = ['n_iter_mean', 'c1_50%', 'c2_50%']
    titles = ['Average No. of Iterations', 'Median Candidate Set Size After Iter 1', 'Median Candidate Set Size After Iter 2']
    for metric, title in zip(metrics, titles):
        plt.figure(figsize=(12, 6))
        sns.barplot(x=metric, y=yval, data=df.sort_values('n_iter_mean'), palette = [P])
        plt.title(title, fontdict={'fontsize': 15})
        # plt.xlim(4, 5)

        for i, row in df.sort_values('n_iter_mean', ascending=True).reset_index(drop=True).iterrows():
            plt.text(row[metric]+0.01, i+0.2, f"{row[metric]:.2f}")
        plt.show()


# ---- GLOBAL LETTER FREQUENCY ---- #
def compute_letter_frequencies(wordset):
    w = wordset.copy()
    for letter in list('abcdefghijklmnopqrstuvwxyz'):
        w[letter] = w.word.str.contains(letter).astype(int)
    return w.iloc[:, 1:]


def compute_score(x, freqs):
    letters = set(x)
    output = 0
    for letter in letters:
        output += freqs[letter]
    return output


def global_lf_scorer(wordset):
    # Compute letter distribution of updated wordset
    wordset_letterdist = compute_letter_frequencies(wordset)
    freqs = wordset_letterdist.sum().to_dict()

    # Obtain scores
    scores = wordset.word.apply(compute_score, freqs=freqs)
    scores = pd.DataFrame({'word': wordset.word, 'score': scores}).sort_values('score', ascending=False)
    
    return scores


def global_lf_pop_scorer(wordset):
    # Compute letter distribution of updated wordset
    wordset_letterdist = compute_letter_frequencies(wordset)
    freqs = wordset_letterdist.sum().to_dict()

    # Obtain scores
    scores = wordset.word.apply(compute_score, freqs=freqs)
    scores = pd.DataFrame({'word': wordset.word, 'score': scores, 'word_freq': wordset.word_freq}) \
        .sort_values(['score', 'word_freq'], ascending=False)
    
    return scores


def find_second_word(word, two_vowel=True):
    letters = list(word)
    candidates = global_scores.loc[global_scores.word.apply(lambda x: all([l not in letters for l in x]))]
    candidates = candidates.loc[candidates.word.apply(lambda x: len(x) == len(set(x)))]
    if two_vowel:
        candidates = candidates.loc[
            candidates.word.apply(lambda x: x.count('a') + x.count('e') + \
                                  x.count('i') + x.count('o') + x.count('u') >= 2)
        ]
    candidates = candidates.groupby('score').first().sort_index(ascending=False)
    return candidates.head(3)


def find_second_word_pop(word, two_vowel=True):
    letters = list(word)
    candidates = global_scores_pop.loc[global_scores_pop.word.apply(lambda x: all([l not in letters for l in x]))]
    candidates = candidates.loc[candidates.word.apply(lambda x: len(x) == len(set(x)))]
    if two_vowel:
        candidates = candidates.loc[
            candidates.word.apply(lambda x: x.count('a') + x.count('e') + \
                                  x.count('i') + x.count('o') + x.count('u') >= 2)
        ]
    candidates = candidates.groupby('score').first().sort_index(ascending=False)
    return candidates.head(3)


# ---- POSITIONAL LETTER FREQUENCY ---- #
def compute_pos_letter_freq(wordset):
    pos_scores = {}
    pos_scores[0] = wordset.word.str[0].value_counts().to_dict()
    pos_scores[1] = wordset.word.str[1].value_counts().to_dict()
    pos_scores[2] = wordset.word.str[2].value_counts().to_dict()
    pos_scores[3] = wordset.word.str[3].value_counts().to_dict()
    pos_scores[4] = wordset.word.str[4].value_counts().to_dict()
    
    return pos_scores


def compute_pos_score(letters, pos_scores):
    output = 0
    for i, letter in enumerate(letters):
        output += pos_scores[i].get(letter, 0)
    return output


def pos_lf_scorer(wordset):
    # Compute positional letter frequencies of updated wordset
    pos_scores = compute_pos_letter_freq(wordset)

    # Obtain scores
    scores = wordset.word.apply(compute_pos_score, pos_scores=pos_scores)
    scores = pd.DataFrame({'word': wordset.word, 'score': scores}).sort_values('score', ascending=False)
    scores = scores.sort_values(['score'], ascending=False)
    
    return scores


def pos_lf_pop_scorer(wordset):
    # Compute positional letter frequencies of updated wordset
    pos_scores = compute_pos_letter_freq(wordset)

    # Obtain scores
    scores = wordset.word.apply(compute_pos_score, pos_scores=pos_scores)
    scores = pd.DataFrame({'word': wordset.word, 'score': scores, 'word_freq': wordset.word_freq}) \
        .sort_values(['score', 'word_freq'], ascending=False)
    
    return scores


def find_second_word_pos(word, two_vowel=True):
    letters = list(word)
    candidates = pos_lf_scores.loc[pos_lf_scores.word.apply(lambda x: all([l not in letters for l in x]))]
    candidates = candidates.loc[candidates.word.apply(lambda x: len(x) == len(set(x)))]
    if two_vowel:
        candidates = candidates.loc[
            candidates.word.apply(lambda x: x.count('a') + x.count('e') + \
                                  x.count('i') + x.count('o') + x.count('u') >= 2)
        ]
    candidates = candidates.groupby('score').first().sort_index(ascending=False)
    return candidates.head(4)


def find_second_word_pos_pop(word, two_vowel=True):
    letters = list(word)
    candidates = pos_lf_scores_pop.loc[pos_lf_scores_pop.word.apply(lambda x: all([l not in letters for l in x]))]
    candidates = candidates.loc[candidates.word.apply(lambda x: len(x) == len(set(x)))]
    if two_vowel:
        candidates = candidates.loc[
            candidates.word.apply(lambda x: x.count('a') + x.count('e') + \
                                  x.count('i') + x.count('o') + x.count('u') >= 2)
        ]
    candidates = candidates.groupby('score').first().sort_index(ascending=False)
    return candidates.head(4)


# ---- DATA ---- #
with open('data/wordle-candidates.json', 'r') as file:
    wordle_candidates = json.load(file)
    
with open('data/wordle-answers.json', 'r') as file:
    wordle_answers = json.load(file)

wordle_candidates = pd.DataFrame(wordle_candidates['words'], columns=['word'])
wordle_answers = pd.DataFrame(wordle_answers['words'], columns=['word'])
wordle_candidates['is_answer'] = 0
wordle_answers['is_answer'] = 1
wordle = wordle_candidates.append(wordle_answers).reset_index(drop=True)

words_all = pd.read_table('data/archive/en_words_1_5-5.txt', delimiter=' ', header=None, index_col=None,
                         names=['word_len', 'word_freq', 'n_articles']).reset_index()
words_all = words_all.rename(columns={'index': 'word'})

# Filter by english
alphabet = list('abcdefghijklmnopqrstuvwxyz')
words_all = words_all.loc[words_all.word.apply(lambda x: all([l in alphabet for l in x]))].reset_index(drop=True)

# Merge additional data
wordle_pop = wordle.merge(words_all[['word', 'word_freq', 'n_articles']], how='left', left_on='word', right_on='word')
wordle_pop = wordle_pop.fillna(0)

# Scores
global_freqs = compute_letter_frequencies(wordle).sum().to_dict()
global_scores = wordle.word.apply(compute_score, freqs=global_freqs)
global_scores = pd.DataFrame({'word': wordle.word, 'score': global_scores}).sort_values('score', ascending=False)

pos_scores = compute_pos_letter_freq(wordle)
pos_lf_scores = wordle.word.apply(compute_pos_score, pos_scores=pos_scores)
pos_lf_scores = pd.DataFrame({'word': wordle.word, 'score': pos_lf_scores}).sort_values('score', ascending=False)

global_scores_pop = global_scores.merge(words_all[['word', 'word_freq', 'n_articles']], how='left', left_on='word', right_on='word')
global_scores_pop = global_scores_pop.fillna(0).sort_values(['score', 'word_freq'], ascending=False)

pos_lf_scores_pop = pos_lf_scores.merge(words_all[['word', 'word_freq', 'n_articles']], how='left', left_on='word', right_on='word')
pos_lf_scores_pop = pos_lf_scores_pop.fillna(0).sort_values(['score', 'word_freq'], ascending=False)