from wordle import WordNetWordle
import argparse
import logging
from config import *
import tweepy
import json

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Wordle')
    parser.add_argument('target_word', type=str, help='target word')
    parser.add_argument('wordle_num', type=int, help='number of wordle')
    args = parser.parse_args()
    log_file = f"wordle_{args.wordle_num}.txt"

    logging.basicConfig(format='%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        filename=log_file,
                        level='DEBUG')

    try:
        with open('history.json') as f:
            history = json.load(f)
    except:
        history = {}
    api = tweepy.Client(consumer_key=api_key,
                        consumer_secret=api_secret,
                        access_token=access_token,
                        access_token_secret=access_token_secret)

    if args.wordle_num not in history:
        w = WordNetWordle()
        score, word, text, luck, word_list = w.play_game(
            args.target_word, args.wordle_num, force_init_guess=initial_guess)
        w.logger.setLevel(logging.CRITICAL)
        response = api.create_tweet(text=text)

        history.update({
            args.wordle_num: {
                'id': response.data['id'],
                'score': score,
                'word': word,
                'text': text,
                'luck': luck,
                'word_list': word_list
            }
        })
        with open('history.json', 'w') as f:
            history = json.dump(history, f, indent=4)
    ## need to make code to check date and tweet log reply to yesterday as well as upload the log?