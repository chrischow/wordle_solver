# Lost for Words: Why There Are Possibly No Best Words for Wordle

Over the past two weeks, I started to see green, yellow, and black/white grids posted on Facebook, but only last week did I start to explore the game of [Wordle](https://www.powerlanguage.co.uk/wordle/). I was hooked - more on discovering a good strategy than on playing the game. And that started me on a journey to build a system to simulate games and derive insights on optimal play.

Wordle and Wordle alone occupied my mind over the past weekend. However, as I progressed in building my solution, I started to see that I was operating with the faulty assumption that the optimal word guesses for a machine are also optimal for a human. Hence, I revised my approach from building a machine that was *neither realistic enough for a human nor optimised enough as a machine* to building two solutions: (a) a pretty optimised solver and (b) a human-like system. And these are the contributions of this post: (1) an explanation of why the "best" combinations of words for Wordle have limited utility, (2) a different approach for a solver implemented in Python (not necessarily the best or most optimised), and (3) a system designed to act in a more human fashion.

## The Game
For the uninitiated, Wordle is Mastermind for 5-letter words. The aim of the game is to guess an undisclosed word in as few steps as possible, and you only have six tries. On each guess, Wordle will tell you if each letter:

- Is in the right spot (green)
- Is in the word, but the wrong spot (yellow)
- Is not in the word at all (grey)

That's all there is to it! It sounds simple, but the game isn't easy because of the sheer number of possibilities. In Wordle, we pick a single word from a set of 2,315 possible solution words in six tries. We also have access to an additional 10,657 words that are accepted as guesses ("support words"). Realistically, since we won't be able to remember offhand which words are candidates and which are solutions, **we are effectively reducing a set of 12,972 words to a single word in six tries**.

> **Note:** The full sets of words can be retrieved from the website's main script. Use your browser's developer console to access it.

## The Word on Wordle
Most of the content on Wordle have focused on the "best" words to use, and not so much on the thinking behind the game. The more popular online sources recommend single words ([CNET](https://www.cnet.com/how-to/best-wordle-start-words-strategies-tips-how-to-win/), [Review Geek](https://www.reviewgeek.com/107930/whats-the-best-wordle-starting-word/)) with some theory, but without supporting data. More technical writers ([Rickard](https://matt-rickard.com/wordle-whats-the-best-starting-word/), [Glaiel](https://medium.com/@tglaiel/the-mathematically-optimal-first-guess-in-wordle-cbcb03c19b0a), [Smyth](https://towardsdatascience.com/what-i-learned-from-playing-more-than-a-million-games-of-wordle-7b69a40dbfdb), [Gafni](https://towardsdatascience.com/automatic-wordle-solving-a305954b746e), [Pastor](https://towardsdatascience.com/hacking-wordle-f759c53319d0)) make recommendations with some technical backing, mostly through simulation.

| Source | Recommendations | Supported by Data |
| :----: | :------- | :---------------: |
| CNET | First guess only: `audio`, `stare`, `teary`, `maker`, `cheat`, `adieu`, `story` |  No |
| USA Today | First guess only: `adieu`, `audio`, `stare`, `roast`, `ratio`, `arise`, `tears`, `roate` (copied from Tyler Glaiel) | No |
| Matt Rickard | First guess only: `soare` | Yes |
| Tyler Glaiel | First guess only: `roate`, `raise` | Yes |
| Kyle Pastor | Two words: `arose-until` | Somewhat |
| Barry Smyth | One word: `tales`; Two words: `cones-trial`; Three words: `hates-round-climb` | Yes |
| Yotam Gafni | One word: `aesir` | Yes |

It goes without saying that the recommendations *without* data are not ideal. These have no concrete indication of either (1) how well they worked in the past, and (2) how well they will work in future. Furthermore, there is no clear metric on which these recommendations are based. While the recommendations supported by data are an improvement, there are some issues with taking them as is. In the next section, we discuss why the various technical recommendations may not be as optimal or actionable as they seem.

## Why the "Best" Isn't Best for You

### What is a Strategy?
First, we need to ask ourselves what a Wordle strategy is. Much of the content focuses on seed words: the initial 1-3 preset guesses. But, a strategy in Wordle is surely more than that. We can analyse this using the six rounds in the game.

In the first round, we submit a good **(1) initial word** and receive feedback.

In the second round, we use the feedback to update our list of candidate words (filtering down) and **(2) rank them**. We must then decide on a **(3) priority**: do we attempt to solve or filter candidates down (cue Wheel of Fortune theme)? This leads us to the submission of another **word** to gather feedback. This process is the same for the third, fourth, fifth, and final rounds.

Combining the things in bold above, the components of a Wordle strategy in my view are: (1) a good seed word to set off the solution on a good or at least feasible path, (2) ranking algorithms to order candidates in terms of their ability to solve the problem vs. filter candidates, and (3) decision rules to prioritise between solving and filtering.

With this definition in place, it becomes clearer that the existing literature only covers one part of a strategy: just the seed word. That would be well and good if the recommendations were based on *heuristics*, and not *outcomes*.

### Heuristic-based vs. Outcome-based Recommendations
A *heuristic-based* approach requires us to make some value judgement about ranking or priorities. It is a set of rules that we set beforehand, and apply in the appropriate scenario. For example, a heuristic for the seed word could be "use the word with the highest sum of letter frequencies" or "use the word with the lowest average number of candidates after filtering". A ranking heuristic could once again be the "sum of letter frequencies".

Projecting outcomes to derive the optimal seed words is a good thought. The question is, what outcomes are being projected? If we're referring to 

Computing **next-step outcomes** 

## Conclusion
- Best seed words are only for a specific and consistent style of play over the long term
- What helps people is a strategy, and a way of thinking about the problem
- There are better words if you use heuristics


First, we have single-word recommendations. Theoretically, it is optimal to use the word (or words) that produces the best average on some metric. This is because we have no information at that point, so we have to rely on broad statistics. Three good choices are the (1) the number of steps to reach a solution, (2) the number of greens and yellows that would be produced, and (3) the size of the candidate set after filtering.

#### Recommendations Based on Projected Game Outcomes
The first solution type sounds great, but may not be effective. This was used separately by Glaiel and Smyth in making their recommendations. What isn't so obvious is that **the recommendations are not entirely applicable to human players**. In generating the game outcomes, specific algorithms had to be used to simulate full games. This means that steps 2 to 6 were played. But what step was taken? Will it still be optimal if I go full potato and guess terrible words like `jujus` and `xylyl`? (I apologise if these are your favourite words)

Surely not! The recommended words worked well under the following conditions:

1. The recommended word(s) were used at the start.
2. In each subsequent round, feedback was input into some algorithm to rank the remaining words. This could have been an extensive search (Glaeil) or heuristics like coverage, letter probabilities, and entropy (Smyth).
3. In the following round, the highest scoring word was used as the guess.

Therefore, the recommendations are optimal **conditional on you playing the game a certain way**. Unless you have perfect memory, lightning-fast computing, are able to consider all or most possibilities, or even copy the algorithms used, the words recommended by the solutions based on average game outcomes may not work out for you.

#### Recommendations Based on Projected Next Step Outcomes
The second and third solutions are relatively straightforward and easy to compute, because they only look one step forward. For the second, take a word you want to evaluate, take a given solution, calculate the feedback, filter the candidate set, and count the number of greens and yellows you would get. The third solution is easy as well: use the same steps, but also count the number of candidates left over from an initial set of 12,972. For both, repeat this for all 2,315 solutions words and take the average.

The strength of these approaches is that they take all available feedback into consideration (as opposed to a two-word or three-word strategy that ignores feedback), and avoid making assumptions about how the game will be played downstream (as opposed to the end outcome-based recommendations). The good news is that each step is individually optimal. The question is then: does this result in optimality overall? Will we solve problems in fewer steps on average?

### Two-word and Three-word Recommendations
First, we can argue from a conceptual point of view that two-word and three-word recommendations are not ideal because they do not incorporate the feedback from prior steps. In theory, these recommendations are only optimal *ex-ante* (before the fact) - they are the best course of action in step 0, before the first guess is made. In practice, the best second guess depends on the feedback from the first guess. I've observed is that the optimal second guess **always** depends on the feedback from the first guess. <show evidence>.

Therefore, the optimal strategy should not involve picking a second and third word before incorporating the feedback from the prior guesses.


### TL;DR
There is no single optimal word or set of words. **How you play the game defines what is optimal**.

We will use experiments to prove this point.

## What is an "Optimal Strategy"?
From a theoretical point of view, the optimal strategy across the six steps (or tries) balances between **solving** (guessing a word that we think is the solution) and **filtering** (using words that will reduce the size of the candidate set as much as possible). Here's the general strategy I've derived from playing the game and designing systems to beat it:

1. **Filter as many words as possible.** We have no information at this point, so there is room for optimising based on general statistics here. The better the first guess, the smaller the candidate set, and the easier the problem downstream.
2. **Filter as many words as possible, *conditional on the feedback from step 1***. While we would earn massive street cred from solving the game in two steps, this is highly improbable. An optimal strategy would not prioritise this. Hence, the best we could do in step 2 is filter candidates as much as possible. In addition, we should also use the information from step 1 as much as possible.
3. **Depends!** If we have obtained enough information (in terms of greens and yellows), perhaps we could go for a solve (like Wheel of Fortune). Otherwise, it may be better to play it safer and choose another word to filter the candidates more.
4. **Again, it depends.** The considerations are the same as step 3. But, this step is where most problems are solved. Perhaps, we could be more aggressive by gearing more toward solving than filtering.
5. **AGAIN, it depends.** The considerations are the same as the prior two steps, but the balance should lie more toward solving than filtering. At this point, the candidate set should have been filtered down to a very manageable level. However, there are edge cases where you have a set of words that differ by only one letter (e.g. fiver, fixer, fiber) or two letters (e.g. shake, brake, flake). More filtering is required for this step by choosing words with the letters that differ. For example, for `fiver / fixer / fiber`, we may guess `box` to split the set into `fiver` and `fixer/fiber`.
6. **Solve.** If it still isn't clear what the solution is, just hazard a guess! What do you have to lose?

## The Players
In this post, I define two solvers for the game: (1) a relatively optimised solver ("the Bot"), and (2) a solver that tries to behave the way a human theoretically would ("the Human").

### The Bot


### The Human

### Results
- Optimal words
- For fun: Head-to-head

What, then, is the way to go?





I wouldn't say that these are the "best" or "most optimal" words for a human player because (1) I cannot fully simulate a human player's actions, which in turn affect there are many definitions of what is optimal. 