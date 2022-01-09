
## Wordle Solver

This can not help you win a live game of [wordle](https://www.powerlanguage.co.uk/wordle/). It can algorithimically solve a wordle like puzzle only if you pass in a target word. In theory, it's making the optimal plays to maximize letter frequency and position frequency. So if you did better than the algorithm, well done! But it exists for comparitive 
use only, not to help people solve the puzzle. (There is no interface to give it feedback, it is designed to play against itself.)

The algorithm does not know the target list from wordle which people have extracted from the source code. It use know the larger 12000+ allowed word list and uses that to restrict its guesses. I think knowing the words can only be from ~2000 words is apriori knowledge that a human wouldn't know. Whereas, the game dosen't penalize you for typing in a word that isn't in its dictionary, so any human could stumble across *aahed* or something as a guess.

It's sort of [a twitter bot](https://twitter.com/thewordlebot) now.

Requires:

* nltk (be sure to download the wordnet,brown,words, and guttenburg corpuses.)
* pandas
  
I can probably ditch the pandas requirement but it made it easier.

## Usage

```
from wordle import Wordle,WordNetWordle
w = Wordle()
w.play_game('siege')
w2 = WordNetWordle()
w2.play_game('siege')
```

## How it works

The alg now uses an idea from [Tyler Glaiel](https://medium.com/@tglaiel/the-mathematically-optimal-first-guess-in-wordle-cbcb03c19b0a) whereas the best guess isn't just one that covers the letter space but that, for every possible remaining answer, what guess on average would reduce the number of possiblities the most.

However, to speed this up I first generate a guess list simply by trying to cover the most letter space of unused letters. This was how the alg worked previously. Then the top 25 of my old approach gets fed into the hypothetical statistical analysis to find the best guess.

The base `Wordle` class because of its limited NLTK dictionary can't solve all words. I think the default now will be the `WordNetWordle` class. If that fails I'll move onto the full 12000+ allowable word list.

Also similar to the post above, I searched for an optimal starting word. However, since I am reluctant to use the ~2000 word target list, I searched the 500 best starting words based on my previous approach (on letter frequency and placement frequency) against all 12000 allowable words. That took 12 cores a few hours, but I found a word that on average reduces the remaining word choices the most. While the code is now too slow to test against all 12,000 words, based on the known 2022 actual Wordle words, the new starting word does find answers faster on average.

## Todo

* Get tweepy working, tweet automatically and 
