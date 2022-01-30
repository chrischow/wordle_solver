# *--------------------*
# | LETTER FREQUENCIES |
# *--------------------*
import pandas as pd

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