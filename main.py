import csv
import importlib
import logging
import operator
import os
import time
import sys

from functools import reduce

from dev.logger import logger_setup
from helpers.config import Config
from helpers.output import Output


def init_loggers():
    logger_setup(
        os.path.join(Config.get('APP_OUTPUT_DIR'), Config.get('APP_LOG_DIR'), Config.get('APP_LOG_DEBUG_FILE')),
        ['ddd_site_parse'], True)

    logger_setup(
        os.path.join(Config.get('APP_OUTPUT_DIR'), Config.get('APP_LOG_DIR'), Config.get('APP_LOG_GRAB_FILE')), [
            'grab.document',
            'grab.spider.base',
            'grab.spider.task',
            'grab.spider.base.verbose'
            'grab.proxylist',
            'grab.stat',
            'grab.script.crawl'
        ]
    )

    logger = logging.getLogger('ddd_site_parse')
    logger.addHandler(logging.NullHandler())

    return logger


def process_stats(stats):
    if not stats:
        return ''

    output = 'Stats:\n'

    _stats = sorted(stats.items(), key=operator.itemgetter(1), reverse=True)
    _max = reduce(lambda a, b: a+b, stats.values())

    for row in _stats:
        output += 'Code: {}, count: {}% ({} / {})'.format(row[0], row[1]/_max * 100, row[1], _max)

    return output


def fix_dirs():
    if not os.path.exists(Config.get('APP_OUTPUT_DIR')):
        os.makedirs(Config.get('APP_OUTPUT_DIR'))

    log_dir = os.path.join(Config.get('APP_OUTPUT_DIR'), Config.get('APP_LOG_DIR'))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)


def parser_loader(file_name):
    return getattr(importlib.import_module('parser.{}'.format(file_name)), 'DSpider')


def load_config():
    if len(sys.argv) > 1:
        Config.load(os.path.join(os.path.dirname(__file__), 'config'), sys.argv[1])
        return True

    return False


def main():
    # load config
    if not load_config():
        exit(2)

    # output config
    Output(True if Config.get('APP_CAN_OUTPUT') == 'True' else False)

    # output dirs
    fix_dirs()

    # log
    logger = init_loggers()
    logger.info(' --- ')
    logger.info('Start app...')

    # output
    output_file_name = time.strftime('%d_%m_%Y') + '.csv'
    output_path = os.path.join(Config.get('APP_OUTPUT_DIR'), output_file_name)

    # bot
    with open(output_path, 'w', newline='', encoding=Config.get('APP_OUTPUT_ENC')) as output:
        writer = csv.writer(output, delimiter=';')

        try:
            threads_counter = int(Config.get('APP_THREAD_COUNT'))
            DSpider = parser_loader(Config.get('APP_PARSER'))
            bot = DSpider(
                thread_number=threads_counter,
                logger_name='ddd_site_parse',
                writer=writer,
                try_limit=int(Config.get('APP_TRY_LIMIT'))
            )
            bot.run()
            logger.info('End with stats: {}'.format(process_stats(bot.status_counter)))

        except Exception as e:
            err = 'App core fatal error: {}'.format(e)

            logger.fatal(err)
            Output.print(err)

    logger.info('End app...\n\n')


if __name__ == '__main__':
    main()
