#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import pathlib
import CCTargets

from HandleTgBuild import HandleTgBuild
from HandleTgClean import HandleTgClean


def ShowGeneralHelp():
    print("Tg is a tool for managing C++ source code.\n"
          "\n"
          "Usage:\n"
          "\n"
          "        tg command [arguments]\n"
          "\n"
          "The commands are:\n"
          "\n"
          "        build       compile targets and dependencies\n"
          "        clean       remove compiled artifacts\n"
          "\n"
          "Environment variables:\n"
          "        TGPATH      path to the root of Tg environment\n"
          "\n")
    sys.exit(-1)


def main():
    if (len(sys.argv) == 1 or 'help' in sys.argv or '-h' in sys.argv or
            '--help' in sys.argv):
        ShowGeneralHelp()
    tgPath = os.getenv('TGPATH')
    assert tgPath is not None, "TGPATH is not set."
    tgPath = pathlib.Path(tgPath).expanduser()
    if sys.argv[1] == 'build':
        HandleTgBuild(tgPath, sys.argv[2:])
    elif sys.argv[1] == 'clean':
        HandleTgClean(tgPath, sys.argv[2:])
    else:
        assert False, '{}: Unknown command.'.format(sys.argv[1])


if __name__ == '__main__':
    main()
