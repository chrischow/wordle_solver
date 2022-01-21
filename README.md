# A Data-Driven Approach to Optimal Play in Wordle

Over the past two weeks, I started to see green, yellow, and grey grids being posted on Facebook. Strange. Only last this week did I learn of [Wordle](https://www.powerlanguage.co.uk/wordle/). And I was hooked, but not on playing the game with my own limited vocabulary, but on how to beat it with any tool possible. This post outlines my solution for optimal Wordle play.

## The Game
For the uninitiated, Wordle is Mastermind for 5-letter words. You have six tries to guess the word. On each guess, Wordle will tell you if each letter:

- Is in the right spot (green)
- Is in the word, but the wrong spot (yellow)
- Is not in the word at all (grey)

That's all there is to it! It sounds simple, but the game isn't easy because of the sheer number of possibilities. You would need sound logical reasoning, a pretty good vocabulary, and some luck - *if you played the game by hand*.

But, consider what is going on under the hood. What we are effectively doing is reducing a set of 2,315 possible words down to a single word in six tries. We have access to an additional 10,657 words that are accepted as guesses. These words are invaluable for the purposes of reducing the set of candidate words.

> **Note:** The full sets of words can be retrieved from the website's main script. Use your browser's developer console to access it.

## Game Strategy
In this post, I'll take you through my stages of thinking about the game and the development of a solution to play the game optimally (using Python):

1. Intuition
2. Global letter frequency
3. Positional letter frequency
4. Word popularity
5. Add-on: Historical trend

## Level 0: Intuition
I didn't actually spend much time playing or reading about the game. In the few games I played, the basic strategy I came up with was to eliminate all vowels and some popular consonants, inspired by Wheel of Fortune's default letters in the final round, `RSTLNE`. To achieve this, I used `aeons, built` or `raise, mount`. I hypothesised that this *should* have restricted the set of feasible words to something manageable.

With my admittedly limited vocabulary and haphazard guessing tactics, this solution did not work out very well for me. If I had spent more time on the game, I may have developed better strategies. But, most who know me will already know what's coming: a data-driven approach.

## Interlude: Game Logic
From here on out, I will be using Python to evaluate ideas to solve Wordle. Hence, I have consolidated some code for game logic in this short subsection.

We have functions to (1) simulate the feedback from Wordle (green/yellow/red), and (2) filter the current candidate set. (1) returns feedback as five-letter strings with `G` for green, `Y` for yellow, and `X` for grey representing each letter for the candidate. For example, the response `XXXGY` to a guess word `codes` indicates that the first three letters are not present in the solution, `e` is a correct letter in the correct position, and `s` is present in the solution, but is in an incorrect position. The response `GGGGG` indicates that the problem has been solved.

```py
# Simulate feedback from Wordle
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

# Filter candidate set
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
```

Next, we need an algorithm for the game. The function below simulates a Wordle game

```py
def sim_wordle(input_word, solution):
    feedback = ''
    wordset = <initialise wordset here>
    tested_words = []
    n_iter = 1

    while feedback != 'GGGGG':

        # Check solution
        feedback = get_feedback(input_word, solution)
        tested_words.append(input_word)

        # Filter wordset
        wordset = filter_wordset(input_word, feedback, wordset)
        wordset = wordset.loc[~wordset.word.isin(tested_words)]

        # Choose next input word
        # ---- Some code here to choose a word ---- #
        input_word = <next word here>
        n_iter += 1
    return n_iter
```

## Idea 1: Global Letter Frequency
Unlike my other posts where I typically survey the literature, identify gaps, and state a clear area of contribution, this project was about discovering a solution for myself. Hence, I did not google for a programming solution straight away. I did, however, glance at some posts that recommended optimal words to try out.

### Key Idea
The first solution I thought of involved letter frequency. The idea was simple: trim the set of candidates as fast as possible by scoring each one by the popularity of its constituent letters. Popularity here refers to the frequency of occurrence of the letter in the universal list of 5-letter words. For example, if `a` occurs 10,000 times in all 5-letter words, `b`, 20,000 times, ..., and `e`, 50,000 times, then the fake word `abcde` would have a score of 150,000 (sum of 10,000, 20,000, 30,000, ..., 50,000).

This scoring system would put words with popular letters at the top of the list. I *theorised* that using these words as guesses would trim the candidate set quickly. But of course, with all technical things, theories add no value until they're validated with data, so let's dive into the implementation!

### Generate Global Letter Frequencies and Word Scores
I used a set of approximately 13k 5-letter words used by Wordle as the corpus. I defined two functions: (1) to take in the corpus saved in a Pandas DataFrame, and adds one column per letter with the counts of that letter in the given word; and (2) to compute scores for each word in the corpus.

```py
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
```

Then, I computed the global letter frequencies for all 13k words (`wordle`) and computed the scores for each word:

```py
global_freqs = compute_letter_distribution(wordle).sum().to_dict()
global_scores = wordle.word.apply(compute_score, freqs=global_freqs)
global_scores = pd.DataFrame({'word': wordle.word, 'score': global_scores}).sort_values('score', ascending=False)
```

![Global letter frequencies]()

![Global scores]()

Finally, I put these functions into the simulation function above. Note that this means we are **recomputing letter frequencies for every updated candidate set**. We do this because the frequency of letters that help to eliminate incorrect solutions changes as the candidate set changes. This contrasts with [Mickey Petersen's solution on Inspired Python](https://www.inspiredpython.com/article/solving-wordle-puzzles-with-basic-python), which re-uses the global letter frequencies in every iteration.

### Results
The simulation started with all 13k Wordle words (2,315 answers + 10,657 supporting words) as the candidate set. For the initial guess, I chose the top 10 words by the global letter frequency score, and four words recommended by [Harry Guinness on Wired.com](https://www.wired.com/story/best-wordle-tips/) based on truly global letter frequency: all words in the Concise Oxford Dictionary. For the former, there were multiple words with the same letter combinations - I simply took the first word. Here is the list of 14 words:

1. `aeros`
2. `aesir`
3. `aloes`
4. `rales`
5. `stoae`
6. `arets`
7. `aisle`
8. `aeons`
9. `nears`
10. `saine`
11. `notes`
12. `resin`
13. `tares` - Note how the letter combination is the same as (6) `arets`
14. `senor`

![Results table]()

Guinness was on to something! Some words were indeed better than others, and his chosen initial words featured in the top 5. In his article, Guinness also recommended using a second word to test other popular letters. Hence, I ran a variant of the simulation, forcing the second one to be one of our choosing. I used the top 5 words based on the average number of turns required for a solution, along with the **next 3 highest-scoring words** for each initial word that met the following criteria:

- Did not have any of the letters in the respective initial word
- Had two vowels in them
- Overall: Had no words if identical letter combinations

I also included Guinness' recommendations for his four chosen initial words.

| Initial Word | Second Words |
| :--------: | :----------- |
| `tares` | `indol`, `noily`, `nicol`, `chino` |
| `saine` | `loury`, `yourt`, `clour` |
| `notes` | `urial`, `drail`, `lairy`, `acrid` |
| `senor` | `tidal`, `laity`, `ictal`, `ducat` |
| `resin` | `dotal`, `octal`, `ploat`, `loath` |

![Global LF Double]()

This was not an extensive search for the optimal solutions, but merely to check if improvements could be made from using two words instead of one. And this was indeed what we found. It was also interesting to see that though they were not optimal, Guinness' recommendations were still near the top!

Overall, the three key insights were:

1. **Two words are indeed better than one.** Guinness was right! 
2. **Letter ordering seems to affect the quality of a candidate.** Although both `tares` and `arets` were among the best initial words to use, they returned different results.
3. **It may not be worth trying to solve problems in two turns.** The proportion of times a problem was solved with two turns or less was extremely small. Luck is likely to be at play for those situations.

## Idea 2: Positional Letter Frequency
Based on the insights gained, I built on the solution with what I termed "positional letter frequency" for simplicity. This refers to the letter frequency based on position of the letter in the word. For example, the letters have very different distributions depending on the position:

![Letter Frequency at Position 1]()

![Letter Frequency at Position 5]()

Why does letter ordering matter? In Wordle, remember that progress is made at the **positional** level: green for a perfect hit of letter and position, yellow for a hit in the letter but not the position, and grey for no hits. Therefore, we can exploit the tendency for letters to be in specific positions. In the above plot, `s` appears 1.5 as many times as `c`, the next highest-occurring letter in the first position. `s` also happens to appear the most in the last position. Notice that 4 of the top 5 initial words have either `s` at the start or at the end!

Therefore, we amend our algorithm to use **letter frequencies in each position** instead of the global letter frequencies for all of Wordle's 5-letter words. This also applies to the updated candidate sets after we have narrowed them down in the course of a game. In implementing the solution, there was a tendency for words with `s` at the start and end to appear at the top of the list. To control for this, we removed words with duplicate letters when choosing the first word. We then tested several of the top words by positional letter frequency, and added Guinness' 4 words for both (1) initial-word-only and (2) two-word configurations as we did earlier.

![Initial word]()

![Two words]()

The results turned out to be worse than using global letter frequencies. This did not feel intuitive to me - using positional letter frequencies should work better because it should slice the candidate set more cleanly. To investigate this result, I implemented both algorithms as pseudo-apps and ran them against the first 20 problems in the [Wordle archive](https://www.devangthakkar.com/wordle_archive/).

For global letter frequencies (`resin, ploat`):

- Wordle 2: `imshy` --> `cissy` --> `kissy` --> `sissy` - solution could **not** have been reached earlier due to the scores
- Wordle 8: `unlaw` --> `fanal` --> `nahal` --> `naval` - solution could have been reached 2 steps earlier
- Wordle 9: `merks` --> `wersh` --> `sered` --> `serge` - did not make it to the solution, `serve`
- Wordle 10: `beath` --> `meath` --> `death` --> `heath` - solution could **not** have been reached earlier due to the scores
- Wordle 12: `odyle` --> `lomed` --> `model` - solution could have been reached 1 step earlier
- Wordle 13: `carby` --> `garum` --> `marka` --> `karma` - solution could have been reached 1 step earlier
- Wordle 18: `hated` --> `acute` --> `amate` --> `abate` - solution could have been reached 1 step earlier

For positional letter frequencies (`pares, doilt`):

- Wordle 9: `herse` --> `serge` --> `serre` --> `serve` - solution could have been reached 2 steps earlier
- Wordle 10: `meath` --> `beath` --> `neath` --> `heath` - solution could have been reached 2 steps earlier
- Wordle 12: `lobed` --> `jodel` --> `yodel` --> `model` - solution could have been reached 2 steps earlier
- Wordle 13: `barry` --> `marah` --> `garum` --> `karma` - solution could have been reached 1 step earlier

In general, both algorithms had their fair share of weird word choices. This is fine if it helps to slice the candidate set well. However, in several cases, the suboptimal ordering of words within the candidate set resulted in solutions being attained much later. And this seemed more prevalent for the positional approach. For the global approach, improvements were difficult because words were ranked purely by overall letter popularity, not **word popularity**, which is something that the positional approach implicitly does.

Another observation is that the positional approach produced more natural or common words (not shown in examples here), whereas the global approach used several obscure, weird words. The advantage from using common words is that Wordle is probably more likely to choose words that people know, therefore increasing the probability of hitting the right word with the positional approach.

Hypothesis: Positional approach will see bigger improvements

The key insight from this section is that the popularity of **words** matters, not just the letters. We will investigate this in the next section.

## Idea 3: Word Popularity
I used data from [Lexipedia](https://en.lexipedia.org/) as a rough gauge of word popularity. This dataset contains the frequency of each word's occurrence in Wikipedia articles, and the count of articles that each word appears in. I merged the data into the DataFrames for the corpus and the scores (global and positional) so that we can use it to order the candidate set with the more natural/intuitive words upfront.