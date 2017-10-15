
import os
import logging

import pprint

pp = pprint.PrettyPrinter(indent=2)

__author__ = "tbl"
__copyright__ = "tbl 2017"
__version__ = "0.1.0"

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)



#
# MAiN
#
if __name__ == "__main__":

    # logger.setLevel(logging.DEBUG)
    logger.setLevel(logging.INFO)

    path = "data-btrx/"
    for f in os.listdir(path):
        if "bt_data__" in f:
            pair, _ = f.split('__')[1].split('.')
            fn = os.path.join(path, f)
            data = []
            with open(fn, 'r') as ifile:
                data = ifile.readlines()
                ifile.close()

            NUM_ENTRIES=len(data[1:])
            NUM_ENTRIES_SUCC=len(filter(lambda x: "NONE" not in x, data[1:]))

            per = 0
            if NUM_ENTRIES > 0:
                per = float((float(NUM_ENTRIES_SUCC) / float(NUM_ENTRIES)) * 100)

            if per > 90:
                print "%9s: %3d/%3d (%4.2f%%)" % (
                    pair,
                    NUM_ENTRIES_SUCC,
                    NUM_ENTRIES,
                    per
                )
