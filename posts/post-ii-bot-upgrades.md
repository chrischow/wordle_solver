
#### Feedback Entropy
This is just a short name for "information entropy of word categories created based on feedback". 

### Simplifying Entropy
First, we explain entropy. I find Vajapeyam's (2014) [paper on Shannon's Entropy metric](https://arxiv.org/ftp/arxiv/papers/1405/1405.2061.pdf) the most useful explanation of the concept. Most articles that explain entropy like to use the word "surprise" - and yes, these authors use scare quotes, which the [MLA Style Center](https://style.mla.org/scare-quotes-origins/) says are *used to convey an ironic, skeptical, or even derisive stance toward the word or phrase they enclose; they signal a nonstandard use, which often **requires a reader to read between the lines to intuit the particular sense intended by the author**.* I understand information as the difference between what you already know compared to what the actualisation of a random variable gives you. If I were to attempt to explain what "surprise" (not scare quoting here) means, it would go something like this:

Let's consider the classic example that uses two-sided coins. Suppose that there are three coins: one is completely biased toward heads, one that turns up heads 75% of the time, and one that is perfectly fair (50-50). We are interested in figuring out how much new information we would be collecting by flipping each of them.

For the biased coin, we *already know that we will get heads on the next flip*. Therefore, there is no point in collecting any new data (i.e. a new flip). That is, there is zero new **information** gained if we collected new data.

For the 75%-heads coin, things are slightly better. We know that we will get heads three quarters of the time, but a random one quarter of the flips would give us tails. Therefore, there is some uncertainty in what would actually happen. Our best baseline would be to generally expect heads, but also expect to be wrong 25% of the time. Consequently, there is *some* point in collecting new data, since we would gain new information on one quarter of the flips.

For the perfectly fair coin, we don't know what the outcome will be on the next flip, because the chances are exactly 50-50. Our baseline knowledge about the discrete outcome is completely uncertain. Therefore, we gain a lot of information whenever any new data on coin flips is collected.

Extending the example to a 100-sided die, suppose we had (1) a completely biased die (100% for one side, 0% for the remaining 99), (2) a somewhat biased die (10% for 10 sides and 0% for the remaining 90), and (3) a completely fair die (1% per side). The thinking is exactly the same: our baseline knowledge will be the highest for (1), the next highest for (2) but still with some uncertainty, and complete uncertainty for (3). Therefore, the result of the die roll would give us the least information for (1), more information for (2), and the most information for (3).

The general idea here is that the more spread out the probabilities/frequencies are, the less baseline knowledge we have. And the less baseline knowledge we have, the more information we would gain when some random variable is actualised. **The more information gained, the greater the entropy**.