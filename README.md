# Wordle2Vec: A Vectorised Approach to Solving Wordle
Over the past few weeks, I started to see green, yellow, and black/white grids posted on Facebook, but only since last week did I start to explore the game of [Wordle](https://www.powerlanguage.co.uk/wordle/) - and I was hooked. I've since been building a system to play the game optimally. This post documents my thoughts on Wordle, and part of my approach to building a solver.

## The Word on Wordle
Numerous articles have already been written on Wordle, covering *breadth* for possible seed words and ranking algorithms for candidate words (see table below). Most of them focus on deciding on the optimal seed word by running simulations. Of these, only one or two elaborate on the overall strategy for the game, and how that strategy is implemented in technical terms. My series of posts contribute through *depth*: we investigate what happens under the hood of a Wordle bot at each step in a typical Wordle game.

> Consider comparing against others' results.

| Source | Approach | Recommendations |
| :----- | :------- | :-------------- |
| [Tyler Glaiel](https://medium.com/@tglaiel/the-mathematically-optimal-first-guess-in-wordle-cbcb03c19b0a) | Expected green / yellow / grey scores; expected remaining candidates | Seed words: `soare`, `roate`, or `raise` |
| [Sejal Dua](https://towardsdatascience.com/a-deep-dive-into-wordle-the-new-pandemic-puzzle-craze-9732d97bf723) | Expected green / yellow / grey scores | Seed words: `soare`, `stare`, `roate`, `raile`, or `arose` |
| [Tom Neill](https://notfunatparties.substack.com/p/wordle-solver) | Expected remaining candidates | Seed word: `raise` |
| [John Stechschulte](https://towardsdatascience.com/optimal-wordle-d8c2f2805704) | Information entropy for expected green / yellow scores | Top 10 seed words: `tares`, `lares`, `rales`, `rates`, `nares`, `tales`, `tores`, `reais`, `dares`, `arles`, or `lores`. Words that get the most coloured tiles and words with the most vowels are not necessarily the best. |
| [Barry Smyth](https://towardsdatascience.com/what-i-learned-from-playing-more-than-a-million-games-of-wordle-7b69a40dbfdb) | Selection of minimum set covers using entropy, letter frequencies, and coverage | One word: `tales`; Two words: `cones-trial`; Three words: `hates-round-climb` |
| [Ben Bellerose](https://towardsdatascience.com/wordle-solver-using-python-3-3c3bccd3b4fb) | Letter position probability | Nil |


## The Game
For the uninitiated, Wordle is Mastermind for 5-letter words. The aim of the game is to guess an undisclosed word in as few steps as possible, and you only have six tries. On each guess, Wordle will tell you if each letter:

- Is in the right spot (green)
- Is in the word, but the wrong spot (yellow)
- Is not in the word at all (grey)

That's all there is to it! It sounds simple, but the game isn't easy for both humans and machines because of the sheer number of possibilities. In Wordle, there are 2,315 possible solution words, and an additional 10,657 words that are accepted as guesses ("support words"). Assuming that we won't be able to remember offhand which words are support words and which are solutions, **we are effectively reducing a set of 12,972 candidates to a single word in six tries**.

> **Note:** The full sets of words can be retrieved from the website's main script. Use your browser's developer console to access it.

## Wordle Strategy
Much like Wheel of Fortune, in Wordle, we balance between **solving** (guessing a word that we think is the solution) and **collecting information** (using words to tease out what letters might be in the solution). A human would probably play with the following strategy:

1. **Round 1: Collect as much information as possible.** We have no information at this point, so we choose a statistically optimal seed word. The better the first guess, the more information we will collect in terms of green, yellow, and grey tiles.
2. **Round 2: Collect as much information as possible *using the feedback from step 1***. While we would earn massive street cred from solving the game in two steps, this is very difficult. Hence, the best we could do in step 2 is collect more information by using a word with completely different letters from the seed word.
3. **Round 3: Depends!** If we have obtained enough information (in terms of greens and yellows), perhaps we could go for a solve (like Wheel of Fortune). Otherwise, it may be better to play it safer and choose another word to get more clues.
4. **Round 4: Again, it depends.** We do the same as we did in step 3. But, this step is where most problems are solved. We could be more aggressive by prioritising a solve over information collection.
5. **Round 5: AGAIN, it depends.** We do the same as we did in steps 3 and 4. But, the balance should lie even more toward solving than collecting information.
6. **Round 6: 100% Solve.** It's entirely possible that you're still left with several feasible solutions by round 6. If it still isn't clear what the solution is, just hazard a guess! What do you have to lose?

As you can probably see, a strategy is more than just the seed word. It also includes (1) decision rules to prioritise solving vs. collecting information, and (2) a ranking algorithm to choose words.

## A Wordle Solver

### Overview
The bot's aim is simple: filter the list of 2,315 possible solutions down to just 1 word in as few tries as possible. Since it does not use a brute force approach to enumerate all possible pathways to the solution, it moves step by step. In each step (round), it ranks words and selects the best one, and then repeats this until it gets the answer.

The key component of the bot is its ranking algorithm. It has several built-in options: (1) letter frequency, (2) expected green, yellow, and grey scores, and (3) a composite of max number of remaining candidates and what I term the *bucket entropy*.

In each step, the bot uses one of the algorithms above to calculate scores for all *relevant* candidates against all feasible solutions. Then, it simply picks the highest-scoring word as the next guess.

Because the ranking algorithm is computationally expensive, we minimise the amount of computations we have to do by iteratively selecting *feasible* solutions and *relevant* candidates. Feasible solutions are those that match the feedback (green/yellow/grey) obtained in prior steps. Relevant candidates are those that still have some ability to filter solutions. Suppose you have 10 feasible solutions remaining, and **none** of them have the letters `a`, `e`, `r`, `s`, and `t` in positions 1 to 5. Then, it makes no sense to continue evaluating candidate words that are made up of only these letters e.g. `aster`, `tease`, or `tress`. This is because they are of no help in filtering the *remaining* feasible solutions. Therefore, we can safely eliminate these words from the candidate set. The leftover candidates are the relevant ones.

### Implementation
Implemented a `Wordle` class with the following methods:

- Standard `__init__(self, candidates, solutions, solution=None, verbose=True)`: To initialise the class with several internal variables. These include:
    - `guess`: The guesses made so far
    - `feedback`: The feedback collected so far
    - `ncands`: The number of remaining candidates after each step
    - `candidates`: The dataframe of relevant candidates
    - `solutions`: The dataframe of feasible solutions
    - `optimisations`: Cache of results from running the ranking algorithms on the existing candidates and solutions
    - `last_optimised`: Record of when each ranking algorithm's cache was stored
    - `step`: Current round in the game
    - `solved`: Game completion status
    - `verbose`: Whether to print out results - turn this off for large scale simulations
    - `solution`: Used only if a solution is provided
- `guess(guess, feedback=None)`: Makes a guess and updates the game state
    - Filters solutions and candidates, but **does not rank them**
    - Logs guesses, feedback, and number of candidates remaining after the step
    - Automatically solves the game if there is only one solution remaining
    - If the object is used as a simulation, no feedback is required
- `status()`: To print out the history of guesses, feedback, and number of candidates remaining after each step thus far
- `optimise(method='ncands')`: Runs ranking algorithms on candidate set with respect to the solution set
    - `ncands`: Composite ranking of the max number of candidates remaining and *bucket entropy*
    - `lf`: Sum of letter frequencies of each word
    - `expected_gyx`: Expected green, yellow, and grey scores
- `records()`: Prints out the history of steps, guesses, feedback, and numbre of candidates remaining after each step
