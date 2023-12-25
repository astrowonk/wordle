from wordle import WordNetWordle2
import argparse
import requests
import datetime
import logging
from config import *
import tweepy
import json
from mastodon import Mastodon

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
    parser.add_argument('--no-mast',
                        action='store_true',
                        help='no mastodon',
                        default=False)

    parser.add_argument('--date',
                        type=str,
                        help='run for this date',
                        default=None)
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
        if not args.date:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
        else:
            date = args.date
        url = f"https://www.nytimes.com/svc/wordle/v2/{date}.json"
        print(f"Retrieving {url}")
        data = requests.get(url).json()
        wordle_num = data['days_since_launch']
        target_word = data['solution']
    else:
        target_word = args.target_word
        wordle_num = args.wordle_num

    w = WordNetWordle2(log_file=log_file)
    score, word, text, luck, word_list = w.play_game(
        target_word, wordle_num, force_init_guess=initial_guess)
    print('solved')
    w.logger.setLevel(logging.CRITICAL)
    entry = [x for x in history if x['wordle_num'] == wordle_num]
    if entry:
        entry = entry[0]
    else:
        entry = {}
    if not args.no_tweet:

        assert entry.get('id') is None, f'wordle {wordle_num} has been tweeted'
        response = api.create_tweet(text=text)
        tweet_id = response.data['id']
    else:
        tweet_id = None
    if not args.no_mast:

        assert entry.get(
            'mast_id') is None, f'wordle {wordle_num} has been tooted'

        text = text + "\n#Wordle"
        mastodon = Mastodon(access_token='mastodon.secret',
                            api_base_url='https://botsin.space')
        response = mastodon.status_post(status=text,
                                        spoiler_text=f"Wordle {wordle_num}")
        mastodon_id = response['id']
    else:
        mastodon_id = None

    history.append({
        'wordle_num': wordle_num,
        'id': tweet_id,
        'masto_id': mastodon_id,
        'score': score,
        'word': word,
        'text': text,
        'luck': luck,
        'word_list': word_list
    })
    with open('better_history.json', 'w') as f:
        json.dump(history, f, indent=4)

    ## need to make code to check date and tweet log reply to yesterday as well as upload the log?
