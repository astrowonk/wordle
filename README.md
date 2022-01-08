
## Wordle Solver

This can not help you win a live game of [wordle](https://www.powerlanguage.co.uk/wordle/). It can algorithimically solve a wordle like puzzle only if you pass in a target word. In theory, it's making the optimal plays to maximize letter frequency and position frequency. So if you did better than the algorithm, you had some good luck! That is the purpose of this class, to - after the fact - compare one's performance against the algorithm.

The algorithm does not know the target list from wordle which people have extracted from the source code. It does know the bigger allowed word list and uses that to restrict its guesses. I think knowing the words can only be from ~2000 words is apriori knowledge and cheating.

It's sort of [a twitter bot](https://twitter.com/thewordlebot) now.

Requires:

* nltk (be sure to download the wordnet,brown,words, and guttenburg corpuses.)
* pandas
  
I can probably ditch the pandas requirement but it made it easier.

There are currently 2 subclasses and the parent class that use different corpuses. Some work better than others depending on the target word. For example `WordnetWordle` can get a hypothetical "wound" word in 6 guesses, but the guttenburg+brown corpuses take 7 tries.

Wheras, the infamous `rebus` from Janury 1, 2022 doesn't exist in guttenburg+brown so one has to use one of the subclasses.

I think the original `Wordle` class with its smaller word list generally performs best, but not always.

## Usage

```
from wordle import Wordle,WordNetWordle
w = Wordle()
w.play_game('siege')
w2 = WordNetWordle()
w2.play_game('siege')
```

## How it works

The alg chooses a starting word based on letter frequency. It then looks at all valid words based on that initial guess. If it's too big (it usually is), its subsequent guesses are designed to eliminate as many letters as possible. It won't just guess a target word unless there are only a few. This means it is not optimized to solve fast, but to solve most words.

There is a lot of parameter tuning that could probably be done on on exactly when it uses a 'wrong' word versus one that could be right.

## Statistics

There are 3 versions (so far) of the algorithm that used different word lists. The original `Wordle` class used the gutenburg + brown corpuses from the [NLTK](https://www.nltk.org). There's also a version seeded with the WordNet corpus, and the actual valid+solution word list that wordle uses.

The original `Wordle` class now removes any words not valid wordle guesses, as does the Wordnet version. That leaves us with word list lengths of:

* Wordle (brown + gutenburg): 3602
* WordnetWordle: 5519
* WordleWordList: 12972

The `Wordle` class has the best overall performance, even on the longer 12,972 list. The code now simply adds the target word to the short word list before solving.

* Success rate: 99.66%, (failures 44/12972)
* Mean guesses: 3.965424 (on successes)

The `WordNetWordle` with its bigger wordlist actually performs worse. 

* Success Rate: 99.34%, (failures 85/12972)
* Mean guesses: 4.091 

`WordleWordList` performs by far the worst.

* Success Rate: 96.1% (failures 505/12972)
* Mean guesses 4.48