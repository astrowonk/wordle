from nltk.corpus import words

import nltk

import re
from functools import partial, lru_cache
from nltk.corpus import gutenberg, brown, wordnet, words
from collections import Counter
import pandas as pd
from exclusions import EXCLUSION_SET
import logging
from copy import deepcopy
import concurrent.futures
from tqdm.notebook import tqdm


def flatten_list(list_of_lists):
    return [y for x in list_of_lists for y in x]


class Wordle():
    good_letters = None

    def __init__(self, log_level="DEBUG", log_file=None):
        self.log_level = log_level
        self.log_file = log_file
        self.init_logging()
        self.image_mapping_dict = {1: "🟨", 0: "⬜", 2: "🟩"}

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
        #self.short_words = short_words
        self.short_words = list(set(short_words).difference(EXCLUSION_SET))

        self.make_frequency_series()

    def init_logging(self):
        self.logger = logging.getLogger(__name__)
        self.log_level = self.log_level
        self.logger.setLevel(self.log_level)
        ch = logging.StreamHandler()
        self.logger.addHandler(ch)

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
        self.score_dict = {
            letter: sum([letter in word for word in self.short_words])
            for letter in 'abcdefghijklmnopqrstuvwxyz'
        }
        letter_rank_series = pd.Series(
            self.score_dict).sort_values(ascending=False)
        self.letter_rank_df = pd.DataFrame(letter_rank_series,
                                           columns=['frequency'
                                                    ]).reset_index()
        self.placement_counter = {
            i: dict(Counter([word[i] for word in self.short_words]))
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

    @lru_cache()
    def score_word(self, guess, answer):
        #print(guess, len(self.short_words))
        assert guess in self.short_words, 'guess not in short words'
        if guess == answer:
            return ["Winner"] * 3 + [[2, 2, 2, 2, 2]]
        match_and_position = [
            2 * int(letter == answer[i]) for i, letter in enumerate(guess)
        ]
        #self.logger.debug(match_and_position)

        remaining_letters = [
            x for i, x in enumerate(answer) if match_and_position[i] != 2
        ]

        #self.logger.debug(remaining_letters)

        def find_non_position_match(remaining_letters, guess):
            """has to be a better way"""
            res = []
            for letter in guess:
                if letter in remaining_letters:
                    res.append(1)
                    remaining_letters.remove(letter)
                else:
                    res.append(0)
            return res

        non_position_match = find_non_position_match(remaining_letters, guess)
        #self.logger.debug(str(non_position_match))
        match_and_position = [
            x or y for x, y in zip(match_and_position, non_position_match)
        ]
        #self.logger.debug(match_and_position)
        return [
            x for i, x in enumerate(guess)
            if match_and_position[i] == 0 and x not in self.answer
        ], [x for i, x in enumerate(guess) if match_and_position[i] > 0], [
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
        self.guess_valid_only = guess_valid_only
        self.force_init_guess = force_init_guess
        if force_init_guess and force_init_guess not in self.short_words:
            self.short_words.append(force_init_guess)
        self.allow_counter_factual = allow_counter_factual

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
            f"Good letters New : {good_letters}, old {self.good_letters}")
        if not self.good_letters:
            self.good_letters = Counter(good_letters)
        else:
            c = Counter(good_letters)
            for key, val in c.items():
                if val > self.good_letters[key]:
                    self.good_letters[key] = val

        ##if len(good_letters) > len(self.good_letters):
        #  self.good_letters = good_letters
        #elif len(good_letters) > 0 and len(good_letters) < len(
        #       self.good_letters) and not all(x in self.good_letters
        #             for x in good_letters):
        #  self.good_letters.extend(good_letters)

    #self.logger.debug(good_letters)
        for x, y in position_tuples:
            self.partial_solution[y] = x

        self.logger.debug(f"partial solution {self.partial_solution}")

    def counter_factual_check(self, hypothetical_answer, limited_word_list):
        res = {}
        for word in set(limited_word_list).difference(self.guesses):
            w = CounterFactual(deepcopy(self), hypothetical_answer)
            w.evaluate_round(word)
            res[word] = (len(w.make_matching_short_words()))
        return res

    def counter_factual_guess(self, top_guess_candidates):
        out = []
        #for word, _, _ in self.make_matching_short_words():
        #    out.append(self.counter_factual_check(word, top_guess_candidates))

        myfunc = partial(self.counter_factual_check,
                         limited_word_list=top_guess_candidates)
        with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
            out = list(
                tqdm(executor.map(
                    myfunc,
                    [word for word, _, _ in self.make_matching_short_words()]),
                     total=len(self.make_matching_short_words())))

        stats = pd.concat([pd.Series(x) for x in out],
                          axis=1).T.mean().sort_values()
        self.logger.setLevel(self.log_level)
        self.logger.debug(
            f"Solution reduction stats by word {stats.head(10).to_dict()}")
        return stats.index[0]

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
             for x in self.short_words
             if self.match_solution(x) and self.check_possible_word(x)
             and self.check_bad_positions(x) and x not in self.guesses],
            key=lambda x: (-x[1], -x[2])
        )  #sorting on total coverage tie breaking with placement score

    def generate_guess(self, i=0):
        """generates a guess based on scoring the dictioray for letter and position coverage"""
        possible_guesses = []

        matching_short_words = self.make_matching_short_words()
        self.logger.debug(
            f"there are {len(matching_short_words)} matching short words")
        if not self.guess_valid_only and (1 < i <= 5) and (
            (sum(self.good_letters.values()) >= 3
             and len(matching_short_words) > 2) or
            (len(self.partial_solution) == 3 and len(matching_short_words) > 2)
                or (len(matching_short_words) > 4)):
            #this line above is like hyperparameter tuning. What's the right
            #blend of parameters? And am I trying to avoid failure or
            # get the best average time to solution and accept more failures?
            def get_sub_string(x, indices):
                return ''.join(x[i] for i in indices)

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
            letters_it_could_be = list(
                letters_it_could_be.intersection(set(self.possible_letters)))

            self.logger.debug(
                f'Too many valid solutions. Possible letters {letters_it_could_be}, possible words are {([x[0] for x in matching_short_words])[:10]}...'
            )
            just_words = [word for word, _, _ in matching_short_words]
            local_score_dict = {
                letter: sum([letter in word for word in just_words])
                for letter in 'abcdefghijklmnopqrstuvwxyz'
            }

            #print(local_score_dict)

            def local_coverage(x):
                return sum(letter in letters_it_could_be for letter in x)

            possible_guesses = sorted(
                [(x, local_coverage(x),
                  self.local_placement_score(
                      x, [word for word, _, _ in matching_short_words]))
                 for x in self.short_words
                 if self.check_duplicate_letters(x) and x not in self.guesses],
                key=lambda x: (x[1], x[2]),
                reverse=True)
            #if len(letters_it_could_be) < len(matching_short_words):
            #    possible_guesses = []
            self.logger.debug(str(possible_guesses[:10]))

        if possible_guesses:
            ## zeroing out the other words in a paradox situation
            matching_short_words = []
            try_these = [x[0] for x in possible_guesses][:25]
            #print(possible_guesses[:20])
            if self.allow_counter_factual:
                counter_factual_guess = self.counter_factual_guess(try_these)
                possible_guesses = [[counter_factual_guess, 0, 0]]
                self.logger.setLevel(self.log_level)

        return possible_guesses, matching_short_words

    def play_game(self,
                  answer,
                  wordle_num=None,
                  guess_valid_only=False,
                  force_init_guess=None,
                  allow_counter_factual=True):
        #assert answer in self.short_words, "answer not in short words"
        remove_answer = False
        assert answer in self.short_words, "Can't solve with limited dictionary, use full dictionary"
        # if answer not in self.short_words:
        #     assert len(answer) == 5, "answer not 5 letters"
        #     self.short_words.append(answer)
        #     self.logger.debug(f"added {answer} temporarily to short words")
        #     remove_answer = True

        self.init_game(answer,
                       guess_valid_only=guess_valid_only,
                       force_init_guess=force_init_guess,
                       allow_counter_factual=allow_counter_factual)
        self.wordle_num = ''
        if wordle_num:
            self.wordle_num = str(wordle_num)
        i = 0
        while True:
            i += 1
            guess_anagram, guess_word_list = self.generate_guess(i)

            self.logger.debug(
                f"{guess_word_list[:10]}, {len(guess_word_list)}")
            if guess_word_list:
                guess = guess_word_list[0][0]
            else:
                guess = guess_anagram[0][0]
            if i == 1 and self.force_init_guess:
                guess = self.force_init_guess
            self.final_list_length = len(guess_word_list)

            self.logger.debug(f"Guess is **{guess}**")
            out = self.evaluate_round(guess)
            if out == 'Winner':
                full_output = ''
                full_output += (
                    f"Wordlebot Wordle {self.wordle_num} {i}/6") + '\n\n'
                for line in self.success_grid:
                    full_output += (''.join(
                        [self.image_mapping_dict[x] for x in line])) + '\n'
                full_output += (
                    f"Luck factor {self.luck_factor or self.final_list_length}\n"
                )

                break
        if remove_answer:
            self.short_words.remove(answer)
        return i, guess, full_output, self.luck_factor or self.final_list_length


class WordNetWordle(Wordle):
    def __init__(self, backtest=False):
        super().__init__()
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
        if not backtest:  #only add these in if we're going forward on a new word, not when we're testing older words
            self.short_words.extend(['hyper', 'unmet'])
        self.make_frequency_series()


class WordListWordle(WordNetWordle):
    def __init__(self, use_anagrams=False, log_level="DEBUG"):
        super().__init__()
        more_short_words = list({
            word
            for word in words.words() if len(word) == 5
            and word.lower() == word and re.match(r"[a-zA-Z]{5}", word)
        })

        self.short_words = list(set(self.short_words + more_short_words))
        self.make_frequency_series()


class WordleWordList(Wordle):
    def __init__(self):
        super().__init__()
        self.short_words = pd.read_csv(
            'https://gist.githubusercontent.com/b0o/27f3a61c7cb6f3791ffc483ebbf35d8a/raw/0cb120f6d2dd2734ded4b4d6e102600a613da43c/wordle-dictionary-full.txt',
            header=None)[0].to_list()
        self.make_frequency_series()


class CounterFactual(Wordle):
    def __init__(self, WordleInstance, hypothesis_word):
        self.__dict__.update(WordleInstance.__dict__)
        self.init_game(hypothesis_word)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel('INFO')

    def init_game(self, answer):
        self.answer = answer
