
## Wordle Solver

This can not help you win a live game of [wordle](https://www.powerlanguage.co.uk/wordle/). It can algorithimically solve a wordle like puzzle only if you pass in a target word. In theory, it's making the optimal plays to maximize letter frequency and position frequency and reduce the remaining possibilities. So if you did better than the algorithm, well done! It exists for comparitive 
use only, not to help people solve the puzzle. (There is no interface to give it feedback, it is designed to play against itself.)

The algorithm **does not know the target list from wordle** which people have extracted from the source code. It uses the larger 12000+ allowed word list to restrict its guesses. I think knowing the words can only be from ~2000 words is apriori knowledge that a human wouldn't know. Whereas, the game dosen't penalize you for typing in a word that isn't in its dictionary, so any human could stumble across *aahed* or something as a guess.

As of 2022-Jan-15, my target word list is as follows:

* The five letter words of the brown, gutenburg, and WordNet corpuses.
* Filter out plural nouns with `nltk` lemmatizer. (there are no plural nouns in the first ~200 wordles)
* Filter out words not in the five letter [GloVe](https://nlp.stanford.edu/projects/glove/) common crawl dictionary.
    * I filtered this with some sort of spelling dictionary for [another project](https://github.com/astrowonk/divergent-association-task), I believe the hunspell spelling dictionary. So I used the filtered dictionary I made there.
    * Since this is in theory in order of frequency I thought about a cutoff around 2500 or so but wordle 37 (`unfed`), ranks 5084 on the GloVe list so I'm probably pushing my luck filtering these words out as it is.

The [Twitter bot](https://twitter.com/thewordlebot) mostly works now.

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

The base `Wordle` class because of its limited NLTK dictionary can't solve all words. The default alg is the `WordNetWordle` class. If that fails I'll move onto the full 12000+ allowable word list.

Also similar to the post above, I searched for an optimal starting word. However, since I am reluctant to use the ~2000 word target list, I searched the 150 best starting words based on my previous approach (on letter frequency and placement frequency) against my target dictionary. 

## Statistics

I have run the latest version of the alg against the first ~200 known Wordle words. 2 of those words aren't in my dictionary. Those two words both are solved in 4 tries with the class with the full ~12,000 word wordle dictionary as target and allowed.

### Full latest alg  (2022-1-15) with starting word from the above analysis and latest target dictionary:

* Score of 2: 3
* Score of 3: 56
* Score of 4: 132
* Score of 5: 17

### Original Code alg, with original starting word from letter/frequency analysis only:

* Score of 3: 46
* Score of 4: 108
* Score of 5: 39
* Score of 6: 4
* Score of 7: 1


