from nltk.corpus import words

import nltk

import re

re.match(r"\w{5}", "_all_")

from nltk.corpus import gutenberg, brown, wordnet, words
from itertools import permutations, product
from collections import Counter
import pandas as pd


def flatten_list(list_of_lists):
    return [y for x in list_of_lists for y in x]


class Wordle():
    def __init__(self):
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
        self.short_words = short_words
        self.make_frequency_series()
        self.placement_counter = {
            i: dict(Counter([word[i] for word in self.short_words]))
            for i in range(5)
        }

    def placement_score(self, word):
        return sum([
            self.placement_counter[i].get(letter, 0)
            for i, letter in enumerate(word)
        ])

    def make_frequency_series(self):
        all_letters = flatten_list([list(x) for x in self.short_words])
        c = Counter(all_letters)
        self.score_dict = dict(c)
        letter_rank_series = pd.Series(
            self.score_dict).sort_values(ascending=False)
        self.letter_rank_df = pd.DataFrame(letter_rank_series,
                                           columns=['frequency'
                                                    ]).reset_index()

    def anagram_maker(self, letters, use_product=False):
        if use_product:
            p = list({''.join(x) for x in product(letters, repeat=5)})
        else:
            p = list({''.join(x) for x in permutations(letters, r=5)})
        return [x for x in p if x in self.short_words]

    def score_word(self, guess, answer):
        assert guess in self.short_words, 'guess not in short words'
        if guess == answer:
            return ["Winner"] * 3 + [[2, 2, 2, 2, 2]]
        match_and_position = [
            2 * int(letter == answer[i]) for i, letter in enumerate(guess)
        ]
        remaining_letters = [
            x for i, x in enumerate(answer) if match_and_position[i] != 2
        ]
        non_position_match = [int(x in remaining_letters) for x in guess]
        match_and_position = [
            sum([x, y]) for x, y in zip(match_and_position, non_position_match)
        ]
        #print(match_and_position)
        return [
            x for i, x in enumerate(guess)
            if match_and_position[i] == 0 and x not in self.answer
        ], [x for i, x in enumerate(guess) if match_and_position[i] > 0], [
            (x, i) for i, x in enumerate(guess) if match_and_position[i] > 1
        ], match_and_position

    def init_game(self, answer):
        self.possible_letters = list('abcdefghijklmnopqrstuvwxyz')
        self.answer = answer
        self.good_letters = []
        self.partial_solution = []
        self.guesses = []
        self.bad_position_dict = []
        self.success_grid = []

    def evaulate_round(self, guess):
        self.guesses.append(guess)
        bad_letters, good_letters, position_tuples, match_and_position = self.score_word(
            guess, self.answer)
        self.success_grid.append(match_and_position)
        self.bad_position_dict.extend([
            (x, z)
            for x, y, z in zip(guess, match_and_position, [0, 1, 2, 3, 4])
            if y == 1
        ])
        self.bad_position_dict = list(set(self.bad_position_dict))
        if bad_letters == 'Winner':
            print('Winner')
            return "Winner"
        for letter in bad_letters:
            if letter in self.possible_letters:
                self.possible_letters.remove(letter)
        self.good_letters = good_letters

        #print(good_letters)
        self.partial_solution = position_tuples

    def coverage_guess(self, guess):
        return sum([self.score_dict[x] for x in guess])

    def match_solution(self, guess):
        return all(letter == guess[i] for letter, i in self.partial_solution)

    @staticmethod
    def check_duplicate_letters(word):
        c = Counter(word)
        if max(c.values()) > 1:
            return False
        return True

    def check_possible_word(self, word):
        """ensures the word has the right minimum count of the letters we know are in the word and no impossible letters"""
        good_counter = Counter(self.good_letters)
        word_count_dict = dict(Counter(word))
        return all(
            word_count_dict.get(key, 0) >= val
            for key, val in good_counter.items()) and all(
                x in self.possible_letters for x in word)

    def check_bad_positions(self, word):
        return all(word[val] != key for key, val in self.bad_position_dict)

    def generate_guess(self):
        #self.good_letters = list(set(self.good_letters))

        possible_letters = self.good_letters
        missing_length = 5 - len(possible_letters)
        search_length = missing_length + 2
        possible_guesses = []
        other_letters = list(
            self.letter_rank_df.query(
                "index in @self.possible_letters and index not in @possible_letters"
            ).head(search_length)['index'])

        letter_pool = list(set(possible_letters + other_letters))
        #   print(letter_pool)
        if len(self.partial_solution) >= 3:
            use_product = True
        else:
            use_product = False

        matching_short_words = [
            (x, self.coverage_guess(x), self.placement_score(x))
            for x in self.short_words
            if self.match_solution(x) and self.check_possible_word(x)
            and self.check_bad_positions(x) and x not in self.guesses
        ]
        if len(matching_short_words) < 8:
            possible_guesses = []
            print("skipping anagram generation")
        else:
            possible_guesses = sorted(
                [(x, self.coverage_guess(x), self.placement_score(x))
                 for x in self.anagram_maker(letter_pool,
                                             use_product=use_product)
                 if self.check_duplicate_letters(x)],
                key=lambda x: (-x[2], -x[1]))

            possible_guesses = [
                x for x in possible_guesses
                if self.match_solution(x[0]) and self.check_possible_word(x[0])
                and self.check_bad_positions(x[0]) and x not in self.guesses
            ]
        #  print(possible_guesses)

        return possible_guesses, sorted(matching_short_words,
                                        key=lambda x: -x[2])

    def play_game(self, answer):
        assert answer in self.short_words, "answer not in short words"
        self.init_game(answer)
        i = 0
        while True:
            i += 1
            guess_anagram, guess_word_list = self.generate_guess()
            #print(guess_anagram[:10], guess_word_list[:10])
            if len(guess_word_list) < 8 or not guess_anagram:
                print("final list, anagram generation not used")
                print(guess_word_list[:10])
                guess = guess_word_list[0][0]
            else:
                p = sorted(list(set(guess_anagram[:10] +
                                    guess_word_list[:10])),
                           key=lambda x: (-x[1], -x[2]))

                p = [x[0] for x in p if self.check_duplicate_letters(x[0])]
                print('final list')
                print(p)
                guess = p[0]
            print(f"Guess is **{guess}**")
            out = self.evaulate_round(guess)
            if out == 'Winner':
                print(f"Winner {guess} in {i} guesses")
                ## need to turn this into an image somehow
                for line in self.success_grid:
                    print(line)
                break


class WordNetWordle(Wordle):
    def __init__(self):
        super().__init__()
        more_short_words = list({
            word
            for word in wordnet.words() if len(word) == 5
            and word.lower() == word and re.match(r"[a-zA-Z]{5}", word)
        })

        self.short_words = list(set(self.short_words + more_short_words))
        self.make_frequency_series()


class WordListWordle(WordNetWordle):
    def __init__(self):
        super().__init__()
        more_short_words = list({
            word
            for word in words.words() if len(word) == 5
            and word.lower() == word and re.match(r"[a-zA-Z]{5}", word)
        })

        self.short_words = list(set(self.short_words + more_short_words))
        self.make_frequency_series()