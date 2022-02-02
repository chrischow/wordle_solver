# Wordle2Vec: A Vectorised Approach to Solving Wordle
Over the past few weeks, I started to see green, yellow, and black/white grids posted on Facebook, but only since last week did I start to explore the game of [Wordle](https://www.powerlanguage.co.uk/wordle/) - and I was hooked. I've since been developing a system to try to play the game optimally.  As I built on the existing work by other authors (the technical ones only), I found conflicting recommendations for the best starting/seed words. My hypothesis was that the best seed word depends on how you play the game. The contribution of this post is therefore to test this hypothesis, and show that other components of a Wordle strategy affect what the best seed words are.

## The Word on Wordle
Numerous articles have already been written on Wordle, many of which focused on starting (seed) words. Most authors simulated a large number of games to identify seed words that produced the best final outcome in terms of the **average number of steps required to solve the games**. However, not all of them did so, and not all of them had other metrics that measured the performance of their Wordle solvers (see table below).

| Source | Approach | Seed Word | Average No. of Steps | Worst Case |
| :----- | :------- | :-------- | :-----: | :--: |
| [Tyler Glaiel](https://medium.com/@tglaiel/the-mathematically-optimal-first-guess-in-wordle-cbcb03c19b0a) | Expected green / yellow scores | `soare` | 3.690 | 8 steps |
| [Tyler Glaiel](https://medium.com/@tglaiel/the-mathematically-optimal-first-guess-in-wordle-cbcb03c19b0a) | Expected remaining candidates | `roate` | 3.494 | 5 steps |
| [Tyler Glaiel](https://medium.com/@tglaiel/the-mathematically-optimal-first-guess-in-wordle-cbcb03c19b0a) | Expected remaining candidates | `raise` | 3.495 | Not provided | 
| [Sejal Dua](https://towardsdatascience.com/a-deep-dive-into-wordle-the-new-pandemic-puzzle-craze-9732d97bf723) | Average green / yellow / grey scores | `soare`, `stare`, `roate`, `raile`, or `arose` | Not provided | Not provided |
| [Tom Neill](https://notfunatparties.substack.com/p/wordle-solver) | Expected remaining candidates | `raise` | Not provided | Not provided |
| [John Stechschulte](https://towardsdatascience.com/optimal-wordle-d8c2f2805704) | Information entropy for expected green / yellow scores | `tares`, `lares`, `rales`, `rates`, `nares`, `tales`, `tores`, `reais`, `dares`, `arles`, or `lores` | Not provided | Not provided |
| [Barry Smyth](https://towardsdatascience.com/what-i-learned-from-playing-more-than-a-million-games-of-wordle-7b69a40dbfdb) | Selection of minimum set covers using entropy, letter frequencies, and coverage | `tales` | 3.66 | Not provided |
| [Barry Smyth](https://towardsdatascience.com/what-i-learned-from-playing-more-than-a-million-games-of-wordle-7b69a40dbfdb) | Selection of minimum set covers using entropy, letter frequencies, and coverage | Two words: `cones-trial` | 3.68 | Not provided |
| [Barry Smyth](https://towardsdatascience.com/what-i-learned-from-playing-more-than-a-million-games-of-wordle-7b69a40dbfdb) | Selection of minimum set covers using entropy, letter frequencies, and coverage | Three words: `hates-round-climb` | Not provided | Not provided |

Another potential issue with the existing content were the conclusions on what was "best". I observed that different authors have recommended different seed words, but used different approaches to run their simulations. This led to the hypothesis that the other components of a Wordle strategy could be the reason why we saw different recommended seed words.

Therefore, building on the literature to test the hypothesis above, we will:

1. Test different configurations of a Wordle strategy on the list of seed words from above i.e. all recommendations
2. Present more metrics on each Wordle solver's performance


## The Game
For the uninitiated, Wordle is Mastermind for 5-letter words. The aim of the game is to guess an undisclosed word in as few steps as possible, and you only have six tries. On each guess, Wordle will tell you if each letter:

- Is in the right spot (green)
- Is in the word, but the wrong spot (yellow)
- Is not in the word at all (grey)

That's all there is to it! It sounds simple, but the game isn't easy for both humans and machines because of the sheer number of possibilities. In Wordle, there are 2,315 possible solution words, and an additional 10,657 words that are accepted as guesses ("support words"). Assuming that we won't be able to remember offhand which words are support words and which are solutions, **we are effectively reducing a set of 12,972 candidates to a single word in six tries**.

> **Note:** The full sets of words can be retrieved from the website's main script. Use your browser's developer console to access it.

## Wordle Strategy
Much like Wheel of Fortune, in Wordle, we balance between **solving** (guessing a word that we think is the solution) and **collecting information** (using words to tease out what letters might be in the solution) in terms of green, yellow, and grey tiles. A human would probably play with the following strategy:

1. **Round 1: Collect as much information as possible.** We have no information at this point, so we choose a statistically optimal seed word. The better the first guess, the more information we will *probably* collect.
2. **Round 2: Collect as much information as possible *using the feedback from round 1***. While we would earn massive street cred from solving the game in two steps, this is very difficult. Hence, the best we could do in round 2 is collect more information by using a word with completely different letters from the seed word.
3. **Round 3: Depends!** If we have obtained enough information, we could go for a solve. Otherwise, it may be better to play it safer and choose another word to get more clues.
4. **Round 4: Again, it depends.** We do the same as we did in round 3. But, this round is where most problems are solved. We could be more aggressive by prioritising a solve over information collection.
5. **Round 5: AGAIN, it depends.** We do the same as we did in rounds 3 and 4. But, the balance should lie even more toward solving than collecting information.
6. **Round 6: 100% Solve.** It's entirely possible that you're still left with several feasible solutions by round 6. If it still isn't clear what the solution is, just hazard a guess! What do you have to lose?

As you can probably see, a strategy is more than just the seed word. It also includes (1) decision rules to prioritise solving vs. collecting information, and (2) a ranking algorithm to choose words.

## A Proposed Wordle Bot

### Overview
The Wordle bot I've built follows the same approach. The start state for the bot has (1) a candidate set comprising all 12,972 accepted words, and (2) a solution set comprising all 2,315 solution words. It will repeatedly measure (1) against (2), and update them both in the course of each game. Note how this is inhuman: it has perfect memory of all words, and is able to perfectly distinguish between accepted words and solution words.

The bot moves one step at a time, doing the same things in every step/round:

1. Use a ranking algorithm to calculate scores for all remaining candidates.
2. Submit the candidate with the best score as the guess for that step.
3. Use the feedback to (a) filter the candidate set and (b) filter the solution set. We also eliminate candidates that were already guessed, and candidates that contain letters that are no longer present in the remaining solution set, i.e. they have no value for filtering candidates further.
4. Put the filtered/remaining candidate and solution sets into a ranking algorithm to calculate scores for each remaining candidate.
5. Sort the remaining candidates by score.
6. Submit the candidate with the best score as the next guess.
7. Repeat from step 1 until the feedback from step 2 is `GGGGG`.

I developed a `Wordle` class to facilitate games, simulated or otherwise. As this is not the focus for the post, I will be skipping over the details of its implementation. I mention it only to show how tidy it makes the code for simulating a game with the bot's general logic:

```py
def play_game(input_word, solution):

    game = Wordle(wordle, wordle_answers, solution=solution, verbose=False)
    
    while not game.solved:
        if game.step == 0:
            game.guess(input_word)
        else:
            game.guess(game.optimisations[method.lower()].word.iloc[0])
        game.optimise(method='expected_gyx', n_jobs=-2)
        
    return game.records()
```

**Note:** It does not use brute force to enumerate all possibilities before deciding on all steps.

### Ranking Algorithms
After much testing, my sense is that the key component of a Wordle strategy is the ranking algorithm (or for humans, the decision process for what word to guess next). We will discuss the evidence for this hypothesis in the next section. My Wordle bot has several built-in options: (1) letter frequency, (2) expected green, yellow, and grey (I term it GYX for simplicity) scores, and (3) max number of remaining candidates. Each algorithm computes scores for all remaining candidates with respect to the remaining solutions.

#### Letter Frequency 
This algorithm ranks words by how popular its constituent letters are. First, it counts the frequencies of letters for all remaining solutions to produce a lookup table with letters as keys and counts as values. Then, it scores each remaining candidate by taking the sum of frequency scores for the letters in that candidate words. Pick the candidate with the highest score.

#### Expected Green/Yellow/Grey Tile Scores
This algorithm ranks words by the expected information gained, based on the number of green tiles and yellow tiles returned, averaged across all remaining solutions. I called this GYX scores for simplicity, and because of the way I coded grey (`X`) in the feedback for the `Wordle` class. For each remaining candidate, the algorithm (1) calculates the feedback from guessing that word against each remaining solution, and (2) calculates `GYX Score = 2 * No. of Greens + No. of Yellows` for each feedback. This produces a list of `N_s = No. of remaining solutions` scores per candidate. Finally, it (3) averages all the scores to produce a single score for that candidate. Pick the candidate with the highest score, because it is expected to return more information in the form of green and yellow tiles.

#### Max Number of Remaining Candidates
This algorithm ranks candidates by how many possibilities they would eliminate / leave behind if guessed, averaged across all remaining solutions. The idea is to choose words that cut the candidate set down the most. For each candidate, the algorithm (1) calculates the feedback from guessing that word against each remaining solution, (2) uses the feedback to filter (a copy of) the remaining candidate set, and (3) counts the number of remaining candidates. That results in a list of `N_s` counts (of remaining candidates) for that candidate. Finally, the algorithm (4) takes the average of all these counts. Pick the candidate with the lowest score, because it eliminates the most possibilities in the worst case.

### Decision Rules
Through some other tests, I discovered some rules that led to improvements in the strategies. However, in view of the amount of content already covered in this post, I'll save these insights for a follow-up post.

## Simulations
I ran each of the words recommended by the various sources from the previous section (see below) against the full set of 2,315 solution words **three times**: once for each ranking algorithm. Overall, that's 17 "best" words by 2,315 solution words by 3 ranking algorithms for a total of **118,065 games of Wordle**.

```
1. arles    10. rates
2. arose    11. reais
3. dares    12. roate
4. lares    13. soare
5. lores    14. stare
6. nares    15. tales
7. raile    16. tares
8. raise    17. tores
9. rales
```

To allow other authors to make comparisons to the strategies tested, I identified three metrics to present for every strategy (seed word + ranking algorithm + decision rules):

1. Average number of steps taken to solve the challenge
2. Solution success rate (out of 2,315 challenges)
3. The proportion of challenges solved within 3 steps or less

To generate these metrics and perform diagnosis on the strategies, I logged the results from each step from the simulations, including (1) the candidates guessed, (2) the feedback, and (3) the number of candidates remaining after each step.

### Results
Overall, the results showed that:

1. The ranking algorithms mattered for all three metrics
2. 

Note that the results presented in this post are for the specific ranking algorithms, **in the way that I implemented them**. 



