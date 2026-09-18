""""""

from .constants import ZFILL_COUNT


def format_label(base_label, count, zfill=ZFILL_COUNT):
    """"""
    return base_label + str(count).zfill(zfill)
