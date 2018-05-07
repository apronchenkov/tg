# -*- coding: utf-8 -*-
import subprocess
import sys


def HandleTgClean(tgPath, args):
    assert not args, "tg clean: Unexpected arguments."
    sys.exit(subprocess.call(['ninja', '-C', str(tgPath), '-t', 'clean']))
