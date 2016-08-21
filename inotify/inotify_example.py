import logging

import inotify.adapters
import re

_DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

_LOGGER = logging.getLogger(__name__)

def _configure_logging():
    _LOGGER.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()

    formatter = logging.Formatter(_DEFAULT_LOG_FORMAT)
    ch.setFormatter(formatter)

    _LOGGER.addHandler(ch)

def _main():
    i = inotify.adapters.Inotify()

    i.add_watch(b'./images')

    try:
        for event in i.event_gen():
            if event is not None:
                (header, type_names, watch_path, filename) = event

                if (re.match(r'(.*)gif$',filename.decode('utf-8')) and type_names == ["IN_CREATE"]):
                    _LOGGER.info("MASK->NAMES=%s "
                                 "WATCH-PATH=[%s] FILENAME=[%s]",
                                 type_names,
                                 watch_path.decode('utf-8'), filename.decode('utf-8'))
    finally:
        i.remove_watch(b'./images')

if __name__ == '__main__':
    _configure_logging()
    _main()
