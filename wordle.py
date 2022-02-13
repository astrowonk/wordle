from nltk import WordNetLemmatizer

import re
from functools import partial
from nltk.corpus import gutenberg, brown, wordnet, words
from collections import Counter
import pandas as pd
from exclusions import EXCLUSION_SET
import logging
from copy import deepcopy
from concurrent.futures import ProcessPoolExecutor
from tqdm.notebook import tqdm


def flatten_list(list_of_lists):
    return [y for x in list_of_lists for y in x]


def get_sub_string(x, indices):
    return ''.join(x[i] for i in indices)


class Wordle():
    max_workers = 8
    good_letters = None
    target_words = None
    top_guess_count = 25
    hard_mode = False

    def __init__(self,
                 log_level="DEBUG",
                 backtest=False,
                 log_file=None,
                 hard_mode=False):
        self.hard_mode = hard_mode
        self.backtest = backtest
        self.log_level = log_level
        self.log_file = log_file
        self.init_logging()
        self.image_mapping_dict = {1: "🟨", 0: "⬜", 2: "🟩"}
        self.make_word_list()
        self.make_frequency_series()
        self.logger.debug(
            f"Wordle inited with {len(self.target_words)} target words and {len(self.short_words)} dictionary words"
        )

    def make_word_list(self):
        short_words_guttenburg = list({
            word
            for word in gutenberg.words() if len(word) == 5
            and word.lower() == word and re.match(r"[a-zA-Z]{5}", word)
        })

        short_words_brown = list({
            word
            for word in brown.words() if len(word) == 5
            and word.lower() == word and re.match(r"[a-zA-Z]{5}", word)
        })
        short_words = list(set(short_words_brown + short_words_guttenburg))
        self.short_words = list(set(short_words).difference(EXCLUSION_SET))

    def init_logging(self):
        self.logger = logging.getLogger(__name__)
        self.log_level = self.log_level
        self.logger.setLevel(self.log_level)
        ch = logging.StreamHandler()
        ch.setLevel(self.log_level)

        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        # add the file handler handlers to the logger
        if self.log_file:
            fh = logging.FileHandler(self.log_file)
            fh.setLevel(self.log_level)
            fh.setFormatter(formatter)

            self.logger.addHandler(fh)

        #  @lru_cache()

    def local_placement_score(self, word, possible_words):
        placement_counter = {
            i: dict(Counter([word[i] for word in possible_words]))
            for i in range(5)
        }
        return sum([
            placement_counter[i].get(letter, 0)
            for i, letter in enumerate(word)
        ])

    def placement_score(self, word):
        return sum([
            self.placement_counter[i].get(letter, 0)
            for i, letter in enumerate(word)
        ])

    def make_frequency_series(self):
        lemma = WordNetLemmatizer()
        #no plurals in the ~200 wordles so far, this is the simplest way to get rid of plurals
        if self.target_words is None:
            self.target_words = [
                word for word in self.short_words
                if (lemma.lemmatize(word) == word or not word.endswith('s'))
            ]
        self.score_dict = {
            letter: sum([letter in word for word in self.target_words])
            for letter in 'abcdefghijklmnopqrstuvwxyz'
        }
        letter_rank_series = pd.Series(
            self.score_dict).sort_values(ascending=False)
        self.letter_rank_df = pd.DataFrame(letter_rank_series,
                                           columns=['frequency'
                                                    ]).reset_index()
        self.placement_counter = {
            i: dict(Counter([word[i] for word in self.target_words]))
            for i in range(5)
        }

    def make_frequency_series_old(self):
        all_letters = flatten_list([list(x) for x in self.short_words])
        c = Counter(all_letters)
        self.score_dict = dict(c)
        letter_rank_series = pd.Series(
            self.score_dict).sort_values(ascending=False)
        self.letter_rank_df = pd.DataFrame(letter_rank_series,
                                           columns=['frequency'
                                                    ]).reset_index()
        self.placement_counter = {
            i: dict(Counter([word[i] for word in self.short_words]))
            for i in range(5)
        }

    @staticmethod
    def get_num_line(guess, answer):
        """Make the wordle score line for a given guess and answer, method borrowed from my Wordle solver class"""
        match_and_position = [
            2 * int(letter == answer[i]) for i, letter in enumerate(guess)
        ]
        remaining_letters = [
            x for i, x in enumerate(answer) if match_and_position[i] != 2
        ]

        # print('remaining letters', remaining_letters)

        def find_non_position_match(remaining_letters, guess):
            """has to be a better way"""
            res = []
            for i, letter in enumerate(guess):
                # print(letter)
                # print(letter in remaining_letters)
                if letter in remaining_letters and match_and_position[i] != 2:
                    res.append(1)
                    remaining_letters.remove(letter)
                else:
                    res.append(0)
            return res

        non_position_match = find_non_position_match(remaining_letters, guess)
        return [x or y for x, y in zip(match_and_position, non_position_match)]

    def score_word(self, guess, answer):
        #print(guess, len(self.short_words))
        if guess == answer:
            return ["Winner"] * 3 + [[2, 2, 2, 2, 2]]
        match_and_position = self.get_num_line(guess, answer)
        assert guess in self.short_words, 'guess not in short words'
        good_letters = [
            x for i, x in enumerate(guess) if match_and_position[i] > 0
        ]
        #self.logger.debug(match_and_position)
        bad_letters = [
            x for i, x in enumerate(guess)
            if match_and_position[i] == 0 and x not in good_letters
        ]

        return bad_letters, good_letters, [
            (x, i) for i, x in enumerate(guess) if match_and_position[i] > 1
        ], match_and_position

    def init_game(self,
                  answer,
                  guess_valid_only=False,
                  force_init_guess=None,
                  allow_counter_factual=False):
        self.possible_letters = list('abcdefghijklmnopqrstuvwxyz')
        self.answer = answer
        self.good_letters = {}
        self.partial_solution = {}
        self.guesses = []
        self.bad_position_dict = []
        self.success_grid = []
        self.luck_factor = None
        self.luck_factor_flag = 0
        self.final_list_length = None
        self.word_list_length = []
        self.guess_valid_only = guess_valid_only
        self.force_init_guess = force_init_guess
        if force_init_guess and force_init_guess not in self.short_words:
            self.short_words.append(force_init_guess)
        self.allow_counter_factual = allow_counter_factual
        self.remaining_words = self.target_words
        self.augmented_guess_count = 0

    def evaluate_round(self, guess):
        self.guesses.append(guess)
        bad_letters, good_letters, position_tuples, match_and_position = self.score_word(
            guess, self.answer)
        # when the word could be mound hound sound etc this is basically luck, so
        # the luck factor indicates how many equally good options there were at the end
        if self.luck_factor_flag and not self.luck_factor:
            self.luck_factor = self.final_list_length
        if sum(match_and_position) == 8 and not self.luck_factor:
            self.luck_factor_flag = 1

        self.success_grid.append(match_and_position)
        self.bad_position_dict.extend([
            (x, z)
            for x, y, z in zip(guess, match_and_position, [0, 1, 2, 3, 4])
            if y == 1
        ])
        self.bad_position_dict = list(set(self.bad_position_dict))
        if bad_letters == 'Winner':
            self.logger.debug('Winner')
            return "Winner"
        for letter in bad_letters:
            if letter in self.possible_letters:
                self.possible_letters.remove(letter)
        self.logger.debug(
            f"Good letters New : {good_letters}, old {self.good_letters}' bad letters {bad_letters}"
        )
        if not self.good_letters:
            self.good_letters = Counter(good_letters)
        else:
            c = Counter(good_letters)
            for key, val in c.items():
                if val > self.good_letters[key]:
                    self.good_letters[key] = val

        for x, y in position_tuples:
            self.partial_solution[y] = x

        self.logger.debug(f"partial solution {self.partial_solution}")

    def counter_factual_check(self, hypothetical_answer, limited_word_list):
        res = {}
        for word in set(limited_word_list).difference(self.guesses):
            w = CounterFactual(
                deepcopy({
                    key: val
                    for key, val in self.__dict__.items() if key != 'v'
                }), hypothetical_answer)
            out = w.evaluate_round(word)
            if out == 'Winner':
                res[word] = 0
            else:
                res[word] = (len(w.make_matching_short_words()))
        return res

    def counter_factual_guess(self, top_guess_candidates):
        out = []
        #for word, _, _ in self.make_matching_short_words():
        #    out.append(self.counter_factual_check(word, top_guess_candidates))

        myfunc = partial(self.counter_factual_check,
                         limited_word_list=top_guess_candidates)
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            out = list(
                tqdm(executor.map(
                    myfunc,
                    [word for word, _, _ in self.make_matching_short_words()]),
                     total=len(self.make_matching_short_words())))

        full_stats = pd.concat([pd.Series(x) for x in out], axis=1).T

        self.logger.setLevel(self.log_level)

        return full_stats

    def coverage_guess(self, guess):
        return sum([self.score_dict[x] for x in set(guess)])

    def match_solution(self, guess):
        return all(letter == guess[i]
                   for i, letter in self.partial_solution.items())

    @staticmethod
    def check_duplicate_letters(word):
        c = Counter(word)
        if max(c.values()) > 1:
            return False
        return True

    def check_valid_hard_guess(self, word):
        if self.hard_mode == False:
            return True
        word_count_dict = dict(Counter(word))
        return all(
            word_count_dict.get(key, 0) >= val for key, val in
            self.good_letters.items()) and self.match_solution(word)

    def check_possible_word(self, word):
        """ensures the word has the right minimum count of the letters we know are in the word and 
        no impossible letters"""
        word_count_dict = dict(Counter(word))
        return all(
            word_count_dict.get(key, 0) >= val
            for key, val in self.good_letters.items()) and all(
                x in self.possible_letters for x in word)

    def check_paradox_word(self, word):
        """ensures no known rejected letters are in the guess"""
        return all(x in self.possible_letters for x in word)

    def score_paradox_word(self, word, letters_it_could_be):
        return sum(x in letters_it_could_be for x in word)

    def check_bad_positions(self, word):
        return all(word[val] != key for key, val in self.bad_position_dict)

    def make_matching_short_words(self):
        return sorted(
            [(x, self.coverage_guess(x), self.placement_score(x))
             for x in self.remaining_words
             if self.match_solution(x) and self.check_possible_word(x)
             and self.check_bad_positions(x) and x not in self.guesses],
            key=lambda x: (-x[1], -x[2])
        )  #sorting on total coverage tie breaking with placement score

    def generate_guess(self, i=0, augmented_guesses=None):
        """generates a guess based on scoring the dictioray for letter and position coverage"""
        possible_guesses = []

        matching_short_words = self.make_matching_short_words()
        self.remaining_words = [x[0] for x in matching_short_words]

        self.logger.debug(
            f"there are {len(matching_short_words)} matching target words: {self.remaining_words[:10]}"
        )
        if not self.guess_valid_only and (1 < i <= 5) and (
            (sum(self.good_letters.values()) >= 3
             and len(matching_short_words) > 2) or
            (len(self.partial_solution) == 3 and len(matching_short_words) > 2)
                or (len(matching_short_words) > 2)):
            #this line above is like hyperparameter tuning. What's the right
            #blend of parameters? And am I trying to avoid failure or
            # get the best average time to solution and accept more failures?

            indices_we_know = [x[1] for x in self.partial_solution.items()]
            missing_indices = [x for x in range(5) if x not in indices_we_know]
            letters_it_could_be = set(
                flatten_list([
                    get_sub_string(x, missing_indices)
                    for x, y, z in matching_short_words
                ]))
            #don't use any letters we know, maximize coverage of new letters
            letters_it_could_be = letters_it_could_be.difference(
                set(self.good_letters.keys()))
            #don't use any letters we know it can't be.

            #I think I should turn this off...not sure it's even doing anything.

            #letters_it_could_be = list(
            #    letters_it_could_be.intersection(set(self.possible_letters)))

            self.logger.debug(
                f'Too many valid solutions. Possible letters {letters_it_could_be}, possible words are {([x[0] for x in matching_short_words])[:10]}...'
            )

            def local_coverage(x):
                return sum(letter in letters_it_could_be for letter in x)

            possible_guesses = sorted(
                [(x, local_coverage(x),
                  self.local_placement_score(
                      x, [word for word, _, _ in matching_short_words]))
                 for x in self.short_words if self.check_duplicate_letters(x)
                 and x not in self.guesses and self.check_valid_hard_guess(x)],
                key=lambda x: (x[1], x[2]),
                reverse=True)

        elif i == 1:
            possible_guesses = sorted(
                [(x, self.coverage_guess(x), self.placement_score(x))
                 for x in self.short_words
                 if self.match_solution(x) and self.check_possible_word(x)
                 and self.check_bad_positions(x) and x not in self.guesses
                 and self.check_valid_hard_guess(x)],
                key=lambda x: (-x[1], -x[2])
            )  #sorting on total coverage tie breaking with placement score
            self.logger.debug(
                f"this should be the full scored short word list{str(possible_guesses[:10])}"
            )

        if possible_guesses:
            ## zeroing out the other words in a paradox situation

            ## TODO clen this up since 'paradox' mode is now the normal model
            matching_short_words = []
            try_these = [x[0] for x in possible_guesses][:self.top_guess_count]

            orig_guess_df = pd.DataFrame(
                possible_guesses[:self.top_guess_count],
                columns=['word', 'local_coverage',
                         'local_placement']).set_index('word')
            if self.allow_counter_factual and i > 1:

                if augmented_guesses:
                    new_guesses = sorted(
                        list(
                            set(augmented_guesses).difference(set(try_these))))
                    self.logger.debug(f"new augmented guesses {new_guesses}")

                    try_these = (list(set(try_these + augmented_guesses)))
                    self.logger.debug(
                        f"total augmented length {len(try_these)}")
                full_data = self.counter_factual_guess(try_these)
                guess = self.determine_final_guess(full_data, orig_guess_df)
                if augmented_guesses:
                    if guess in new_guesses:
                        self.logger.debug(
                            f"guess {guess} is in augmented guesse")
                        self.augmented_guess_count += 1

                possible_guesses = [[guess, 0, 0]]
                self.logger.setLevel(self.log_level)
            # self.logger.debug(
            #     f"Counter factual data {res_df.to_json(indent=4)}")

        return possible_guesses, matching_short_words

    def augment_guesses(self, possible_guesses):
        """
        empty in base class
        """
        return possible_guesses

    def determine_final_guess(self, counter_factual_data, orig_guess_df):
        """what statistic should determine the next guess. This uses mean, but
        argument could be made to alwasy minimize the max"""
        summary_stats = counter_factual_data.describe().T[[
            'mean', 'std', 'max'
        ]].sort_values(['mean', 'std', 'max'])
        res_df = orig_guess_df.join(summary_stats).sort_values(
            ['mean', 'std', 'max', 'local_coverage', 'local_placement'],
            ascending=[True, True, True, False, False])
        self.logger.debug(
            f"Solution reduction stats by word {res_df.head(10).reset_index().to_dict(orient='records')}"
        )

        return res_df.index[0]

    def play_game(self,
                  answer,
                  wordle_num=None,
                  guess_valid_only=False,
                  force_init_guess=None,
                  allow_counter_factual=True,
                  i=0):
        remove_answer = False
        assert answer in self.target_words, "Can't solve with limited dictionary, use full dictionary"

        self.init_game(answer,
                       guess_valid_only=guess_valid_only,
                       force_init_guess=force_init_guess,
                       allow_counter_factual=allow_counter_factual)
        self.wordle_num = ''
        if wordle_num:
            self.wordle_num = str(wordle_num)

        while True:
            i += 1
            guess_anagram, guess_word_list = self.generate_guess(i)

            self.logger.debug(
                f"{guess_word_list[:10]}, {len(guess_word_list)}")
            #(guess_word_list, guess_anagram, self.remaining_words)
            if guess_word_list:
                guess = guess_word_list[0][0]
            else:
                guess = guess_anagram[0][0]
            if i == 1 and self.force_init_guess:
                guess = self.force_init_guess

            self.logger.info(f"Guess is **{guess}**")
            out = self.evaluate_round(guess)
            self.final_list_length = len(self.remaining_words)
            self.word_list_length.append(self.final_list_length)

            if out == 'Winner':
                full_output = self.create_output(i)

                break
        if remove_answer:
            self.short_words.remove(answer)
        return i, guess, full_output, self.luck_factor or self.final_list_length, self.guesses

    def create_output(self, winning_round):
        full_output = ''
        temp_dict = {key: val for key, val in enumerate(self.word_list_length)}
        full_output += (
            f"Wordlebot Wordle {self.wordle_num} {winning_round}/6") + '\n\n'
        for i, line in enumerate(self.success_grid):
            full_output += (''.join([self.image_mapping_dict[x] for x in line
                                     ])) + f" {temp_dict.get(i+1,0)} left\n"
        #full_output += (f"Luck factor {self.final_list_length}\n")
        return full_output


class WordNetWordle(Wordle):
    def make_word_list(self):
        super().make_word_list()
        more_short_words = list({
            word
            for word in wordnet.words() if len(word) == 5
            and word.lower() == word and re.match(r"[a-zA-Z]{5}", word)
        })

        self.short_words = list(set(self.short_words + more_short_words))
        official_list = set(
            pd.read_csv('wordle-dictionary-full.txt',
                        header=None)[0].to_list())
        self.short_words = list(
            set(self.short_words).intersection(official_list))
        ## adding in two missing previous wordle answers which...may or may not make it perform better.
        if not self.backtest:  #only add these in if we're going forward on a new word, not when we're testing older words
            # should I remove prev wordles or add them? Hmmm... maybe add to short_words and remove from target
            self.short_words.extend(['hyper', 'unmet'])


class WordleWordList(Wordle):
    def make_word_list(self):
        self.short_words = pd.read_csv(
            'https://gist.githubusercontent.com/b0o/27f3a61c7cb6f3791ffc483ebbf35d8a/raw/0cb120f6d2dd2734ded4b4d6e102600a613da43c/wordle-dictionary-full.txt',
            header=None)[0].to_list()


class CounterFactual(Wordle):
    def __init__(self, wordle_dict, hypothesis_word):
        self.__dict__.update(wordle_dict)
        assert 'v' not in self.__dict__.keys(), 'what is this?'
        self.init_game(hypothesis_word)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel('INFO')

    def init_game(self, answer, **kwargs):
        self.answer = answer


class WordNetWordle2(WordNetWordle):
    """This is the default class for the twitter bot for now."""
    top_guess_count = 40

    def make_word_list(self):
        super().make_word_list()
        lemma = WordNetLemmatizer()
        #no plurals in the ~200 wordles so far, this is the simplest way to get rid of plurals

        self.target_words = [
            word for word in self.short_words
            if (lemma.lemmatize(word) == word or not word.endswith('s'))
        ]
        official_list = pd.read_csv('wordle-dictionary-full.txt',
                                    header=None)[0].to_list()
        self.short_words = official_list
        self.target_words = list(
            set(self.target_words).intersection(set(official_list)))

        #filtering additional odd words
        common_words = set(
            pd.read_csv('glove_five_letter_common.csv',
                        header=None)[0].to_list())
        self.target_words = list(
            set(self.target_words).intersection(set(common_words)))


class WordNetMinMix(WordNetWordle2):
    def determine_final_guess(self, counter_factual_data, orig_guess_df):
        """what statistic should determine the next guess. This mins the max"""
        summary_stats = counter_factual_data.describe().T[[
            'mean', 'std', 'max'
        ]].sort_values(['mean', 'std', 'max'])
        res_df = orig_guess_df.join(summary_stats).sort_values(
            ['max', 'std', 'mean', 'local_coverage', 'local_placement'],
            ascending=[True, True, True, False, False])
        self.logger.debug(
            f"Solution reduction stats by word {res_df.head(10).reset_index().to_dict(orient='records')}"
        )

        return res_df.index[0]


class WordleR(Wordle):
    """Using the wordle R list from:
    
    https://github.com/TheRensselaerIDEA/WordleR
    
    """
    def __init__(self,
                 log_level="DEBUG",
                 backtest=False,
                 log_file=None,
                 n=3000):
        self.n_words = n

        super().__init__(log_level, backtest, log_file)

    def make_word_list(self):
        all_words = pd.read_csv("sorted_list.csv", sep=';')['word']
        if (n := self.n_words) is None:
            n = len(all_words)

        self.target_words = pd.read_csv("sorted_list.csv",
                                        sep=';')['word'].head(n).tolist()
        self.short_words = pd.read_csv("sorted_list.csv",
                                       sep=';')['word'].head(n).tolist()


class Primel(Wordle):
    """for the primel game here: https://converged.yt/primel/"""
    def make_word_list(self):
        primes = pd.read_csv('primes-to-100k.txt', header=None)[0].astype(str)
        prime_list = [x for x in primes if len(x) == 5]
        self.target_words = self.short_words = prime_list

    def make_frequency_series(self):

        self.score_dict = {
            letter: sum([letter in word for word in self.target_words])
            for letter in '0123456789'
        }
        letter_rank_series = pd.Series(
            self.score_dict).sort_values(ascending=False)
        self.letter_rank_df = pd.DataFrame(letter_rank_series,
                                           columns=['frequency'
                                                    ]).reset_index()
        self.placement_counter = {
            i: dict(Counter([word[i] for word in self.target_words]))
            for i in range(5)
        }

    def init_game(self,
                  answer,
                  guess_valid_only=False,
                  force_init_guess=None,
                  allow_counter_factual=False):
        super().init_game(answer, guess_valid_only, force_init_guess,
                          allow_counter_factual)
        self.possible_letters = list('0123456789')


class WordNetWordle3(WordNetWordle2):
    """An even slower subclass which doesn't just computer the mean number of remaining words after each possible guess
    but plays a naive game to the end and computes stats based on the final score. Unclear if it outperforms its parent class yet
    as it is so much slower testing will take a while."""
    def counter_factual_check(self, hypothetical_answer, limited_word_list):
        res = []
        for word in set(limited_word_list).difference(self.guesses):
            #   print(
            #       f"TEsting guess {word} against hypothetical answer {hypothetical_answer}"
            #   )
            full_res = {}
            w = CounterFactual(
                deepcopy({
                    key: val
                    for key, val in self.__dict__.items() if key != 'v'
                }), hypothetical_answer)
            out = w.evaluate_round(word)
            if out == 'Winner':
                full_res['words_left'] = 0
            else:
                full_res['words_left'] = (len(w.make_matching_short_words()))
            if word == hypothetical_answer:
                score = 0
            else:
                w.allow_counter_factual = False
                score, _, _, _, _ = w.play_game(
                    hypothetical_answer,
                    allow_counter_factual=False,
                )
            full_res['final_score'] = score
            full_res['word'] = word
            full_res['hypothetical_answer'] = hypothetical_answer
            res.append(full_res)
        return res

    def determine_final_guess(self, counter_factual_data, orig_guess_df):
        """what statistic should determine the next guess. This mins the max"""
        res_df = counter_factual_data.groupby('word')[[
            'words_left', 'final_score'
        ]].max().sort_values(['final_score', 'words_left'])
        self.logger.debug(
            f"Solution reduction stats by word {res_df.head(10).reset_index().to_dict(orient='records')}"
        )

        return res_df.index[0]

    def counter_factual_guess(self, top_guess_candidates):
        out = []
        #for word, _, _ in self.make_matching_short_words():
        #    out.append(self.counter_factual_check(word, top_guess_candidates))

        myfunc = partial(self.counter_factual_check,
                         limited_word_list=top_guess_candidates)
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            out = list(
                tqdm(executor.map(
                    myfunc,
                    [word for word, _, _ in self.make_matching_short_words()]),
                     total=len(self.make_matching_short_words())))

        full_stats = pd.concat([pd.DataFrame(x) for x in out])

        self.logger.setLevel(self.log_level)

        return full_stats
