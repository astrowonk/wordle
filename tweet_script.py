from wordle import WordNetWordle2
import argparse
import requests
import datetime
import logging
from config import initial_guess
import json
from mastodon import Mastodon

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Wordle')
    parser.add_argument('target_word', type=str, help='target word', nargs='?', default=None)
    parser.add_argument(
        'wordle_num', type=int, help='number of wordle', nargs='?', default=None
    )
    parser.add_argument('--no-tweet', action='store_true', help='no tweet', default=False)
    parser.add_argument('--no-mast', action='store_true', help='no mastodon', default=False)

    parser.add_argument('--date', type=str, help='run for this date', default=None)
    args = parser.parse_args()
    log_file = f'wordle_{args.wordle_num}.txt'

    # logging.basicConfig(format='%(asctime)s %(message)s',
    #                     datefmt='%m/%d/%Y %I:%M:%S %p',
    #                     filename=log_file,
    #                     level='DEBUG')

    try:
        with open('better_history.json') as f:
            history = json.load(f)
    except:
        history = []
    if not (args.target_word and args.wordle_num):
        if not args.date:
            date = datetime.datetime.now().strftime('%Y-%m-%d')
        else:
            date = args.date
        url = f'https://www.nytimes.com/svc/wordle/v2/{date}.json'
        print(f'Retrieving {url}')
        data = requests.get(url).json()
        wordle_num = data['days_since_launch']
        target_word = data['solution']
    else:
        target_word = args.target_word
        wordle_num = args.wordle_num

    w = WordNetWordle2(log_file=log_file)
    try:
        score, word, text, luck, word_list = w.play_game(
            target_word, wordle_num, force_init_guess=initial_guess
        )
    except AssertionError:
        w.target_words = w.short_words
        score, word, text, luck, word_list = w.play_game(
            target_word, wordle_num, force_init_guess=initial_guess
        )

        pass
    print('solved')
    w.logger.setLevel(logging.CRITICAL)
    entry = [x for x in history if x['wordle_num'] == wordle_num]
    if entry:
        entry = entry[0]
    else:
        entry = {}
    if not args.no_mast:
        assert entry.get('mast_id') is None, f'wordle {wordle_num} has been tooted'

        text = text + '\n#Wordle'
        mastodon = Mastodon(access_token='mastodon.secret', api_base_url='https://vmst.io')
        response = mastodon.status_post(status=text, spoiler_text=f'Wordle {wordle_num}')
        mastodon_id = response['id']
    else:
        mastodon_id = None

    history.append(
        {
            'wordle_num': wordle_num,
            'masto_id': mastodon_id,
            'score': score,
            'word': word,
            'text': text,
            'luck': luck,
            'word_list': word_list,
        }
    )
    with open('better_history.json', 'w') as f:
        json.dump(history, f, indent=4)

    ## need to make code to check date and tweet log reply to yesterday as well as upload the log?
