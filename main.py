# coding:utf8


import traceback
import os

from program import VKBotApp
from bot.utils import PATH, DATA_PATH, save_error


def main():
    try:
        if not os.path.exists(PATH) and PATH:
            os.makedirs(PATH)
        if not os.path.exists(DATA_PATH):
            os.makedirs(DATA_PATH)

        VKBotApp().run()
    except Exception:
        error_text = traceback.format_exc()
        save_error(error_text)

if __name__ == '__main__':
    main()
