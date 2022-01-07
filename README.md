
## Wordle Solver

This can not help you win a live game of wordle. It can algorithimically solve a wordle like puzzle only if you pass in a target word. In theory, it's making the optimal plays to maximize letter frequency and position frequency. So if you did better than the algorithm, you had some good luck! That is the purpose of this class, to - after the fact - compare one's performance against the algorithm.

I may turn this into a twitter bot at some point.

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

## Todo

It's doing something weird with `amaze`.