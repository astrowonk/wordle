from wordle import WordNetWordle
import argparse
import logging
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

    w = WordNetWordle()
    score, word, text, luck = w.play_game(args.target_word,
                                          args.wordle_num,
                                          force_init_guess='lares')

    print(text)