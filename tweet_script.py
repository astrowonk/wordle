from wordle import WordNetWordle2
import argparse
import requests
import datetime
import logging
from config import *
import tweepy
import json

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Wordle')
    parser.add_argument('target_word',
                        type=str,
                        help='target word',
                        nargs='?',
                        default=None)
    parser.add_argument('wordle_num',
                        type=int,
                        help='number of wordle',
                        nargs='?',
                        default=None)
    parser.add_argument('--no-tweet',
                        action='store_true',
                        help='no tweet',
                        default=False)
    args = parser.parse_args()
    log_file = f"wordle_{args.wordle_num}.txt"

    # logging.basicConfig(format='%(asctime)s %(message)s',
    #                     datefmt='%m/%d/%Y %I:%M:%S %p',
    #                     filename=log_file,
    #                     level='DEBUG')

    try:
        with open('better_history.json') as f:
            history = json.load(f)
    except:
        history = []
    api = tweepy.Client(consumer_key=api_key,
                        consumer_secret=api_secret,
                        access_token=access_token,
                        access_token_secret=access_token_secret)

    if not (args.target_word and args.wordle_num):
        date = datetime.datetime.now().strftime("%Y-%m-%d")
        url = f"https://www.nytimes.com/svc/wordle/v2/{date}.json"
        print(f"Retrieving {url}")
        data = requests.get(url).json()
        print(data)
        wordle_num = data['days_since_launch']
        target_word = data['solution']
    else:
        target_word = args.target_word
        wordle_num = args.wordle_num
    assert wordle_num not in [x['wordle_num'] for x in history
                              ], f"{wordle_num} in history file."

    w = WordNetWordle2(log_file=log_file)
    score, word, text, luck, word_list = w.play_game(
        target_word, wordle_num, force_init_guess=initial_guess)
    w.logger.setLevel(logging.CRITICAL)
    if not args.no_tweet:
        response = api.create_tweet(text=text)
        tweet_id = response.data['id']
    else:
        tweet_id = None

    history.append({
        'wordle_num': args.wordle_num,
        'id': tweet_id,
        'score': score,
        'word': word,
        'text': text,
        'luck': luck,
        'word_list': word_list
    })
    with open('better_history.json', 'w') as f:
        json.dump(history, f, indent=4)

    ## need to make code to check date and tweet log reply to yesterday as well as upload the log?