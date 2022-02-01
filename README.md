# Wordle2Vec: A Vectorised Approach to Solving Wordle
Over the past few weeks, I started to see green, yellow, and black/white grids posted on Facebook, but only since last week did I start to explore the game of [Wordle](https://www.powerlanguage.co.uk/wordle/) - and I was hooked. I've since been building a system to play the game optimally. This post documents my thoughts on Wordle, and part of my approach to building a solver.

## The Word on Wordle
Numerous articles have already been written on Wordle, covering *breadth* for possible seed words and ranking algorithms for candidate words (see table below). Most of them focus on deciding on the optimal seed word by running simulations. Of these, only one or two elaborate on the overall strategy for the game, and how that strategy is implemented in technical terms. My series of posts contribute through *depth*: we investigate what happens under the hood of a Wordle bot at each step in a typical Wordle game.

> Talk about how articles say this seed word is the best or that is the best. Ultimately, it depends on the approach that their solvers used. If you change the algorithm, the best word might change. We need a standardised way to compare Wordle solvers.

> Propose a framework (lol). Each submission must have the full strategy: the seed word, the ranking algorithm, other decision rules (e.g. prioritising between solving vs. filtering, dealing with specific cases). Each submission must be measured in terms of some standard metrics: average number of steps (general solving ability), failure rate (success), percent of games solved in 3 steps or under (street cred value).

> Seed words matter, but they're optimal conditional on the other components of the strategy. Need a more structured way to evaluate strategies.

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

## Feedback Bucket Entropy
This is just a short name for "information entropy of words bucketed across feedback codes". 

### Simplifying Entropy
First, we explain entropy. I find Vajapeyam's (2014) [paper on Shannon's Entropy metric](https://arxiv.org/ftp/arxiv/papers/1405/1405.2061.pdf) the most useful explanation of the concept. Most articles that explain entropy like to use the word "surprise" - and yes, these authors use scare quotes, which the [MLA Style Center](https://style.mla.org/scare-quotes-origins/) says are *used to convey an ironic, skeptical, or even derisive stance toward the word or phrase they enclose; they signal a nonstandard use, which often **requires a reader to read between the lines to intuit the particular sense intended by the author**.* I understand information as the difference between what you already know compared to what the actualisation of a random variable gives you. If I were to attempt to explain what "surprise" (not scare quoting here) means, it would go something like this:

Let's consider the classic example that uses two-sided coins. Suppose that there are three coins: one is completely biased toward heads, one that turns up heads 75% of the time, and one that is perfectly fair (50-50). We are interested in figuring out how much new information we would be collecting by flipping each of them.

For the biased coin, we *already know that we will get heads on the next flip*. Therefore, there is no point in collecting any new data (i.e. a new flip). That is, there is zero new **information** gained if we collected new data.

For the 75%-heads coin, things are slightly better. We know that we will get heads three quarters of the time, but a random one quarter of the flips would give us tails. Therefore, there is some uncertainty in what would actually happen. Our best baseline would be to generally expect heads, but also expect to be wrong 25% of the time. Consequently, there is *some* point in collecting new data, since we would gain new information on one quarter of the flips.

For the perfectly fair coin, we don't know what the outcome will be on the next flip, because the chances are exactly 50-50. Our baseline knowledge about the discrete outcome is completely uncertain. Therefore, we gain a lot of information whenever any new data on coin flips is collected.

Extending the example to a 100-sided die, suppose we had (1) a completely biased die (100% for one side, 0% for the remaining 99), (2) a somewhat biased die (10% for 10 sides and 0% for the remaining 90), and (3) a completely fair die (1% per side). The thinking is exactly the same: our baseline knowledge will be the highest for (1), the next highest for (2) but still with some uncertainty, and complete uncertainty for (3). Therefore, the result of the die roll would give us the least information for (1), more information for (2), and the most information for (3).

The general idea here is that the more spread out the probabilities/frequencies are, the less baseline knowledge we have. And the less baseline knowledge we have, the more information we would gain when some random variable is actualised. **The more information gained, the greater the entropy**.