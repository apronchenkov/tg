# -*- coding: utf-8 -*-

import re
import pathlib

_TOKEN = '(?:[0-9A-Za-z_+-][0-9A-Za-z._+-]*)'

_NAME_RE = re.compile('^{TOKEN}$'.format(TOKEN=_TOKEN))

_ABSOLUTE_PATH_RE = re.compile('^/(?:/{TOKEN})*$'.format(TOKEN=_TOKEN))

_LOCAL_PATH_RE = re.compile('^@(?:/{TOKEN})*$'.format(TOKEN=_TOKEN))

_RELATIVE_PATH_RE = re.compile(
    '^(?:|{TOKEN}(?:/{TOKEN})*)$'.format(TOKEN=_TOKEN))

_PATH_RE = re.compile(
    '^(?:|(?:{TOKEN}|@|/)(?:/{TOKEN})*)$'.format(TOKEN=_TOKEN))


def IsName(string):
    return isinstance(string, str) and _NAME_RE.search(string) is not None


def IsAbsolutePath(string):
    return isinstance(string,
                      str) and _ABSOLUTE_PATH_RE.search(string) is not None


def IsLocalPath(string):
    return isinstance(string,
                      str) and _LOCAL_PATH_RE.search(string) is not None


def IsRelativePath(string):
    return isinstance(string,
                      str) and _RELATIVE_PATH_RE.search(string) is not None


def IsPath(string):
    return isinstance(string, str) and _PATH_RE.search(string) is not None


def CombinePaths(headPart, *tailParts, findLocalRootFn):
    assert IsAbsolutePath(
        headPart), '{}: The first part must be an absolute one.'.format(
            headPart)
    result = headPart
    for part in filter(None, tailParts):
        if IsAbsolutePath(part):
            result = part
        elif IsLocalPath(part):
            localRoot = findLocalRootFn(result)
            assert localRoot is not None, '{}: No local root found from here.'.format(
                result)
            result = localRoot + part[1:]
        elif IsRelativePath(part):
            result = result + '/' + part
        else:
            assert false, '{}: Each trailing path must be a path.'.format(part)
    return result


class SrcFs:
    def __init__(self, srcRoot):
        assert isinstance(srcRoot, pathlib.Path)
        self.__srcRoot = srcRoot
        self.__localRootCache = dict()
        assert self.__srcRoot.is_dir()

    def IsName(self, string):
        return IsName(string)

    def IsAbsolutePath(self, string):
        return IsAbsolutePath(string)

    def IsLocalPath(self, string):
        return IsLocalPath(string)

    def IsRelativePath(self, string):
        return IsRelativePath(string)

    def IsPath(self, string):
        return IsPath(string)

    def _Exists(self, path):
        # assert IsAbsolutePath(path)
        return not path.endswith('/') and (self.__srcRoot / path[2:]).exists()

    def _IsLocalRoot(self, path):
        # assert IsAbsolutePath(path)
        return (self._Exists(path + '/.git') or self._Exists(path + '/.hg'))

    def _FindLocalRoot(self, path):
        # assert IsAbsolutePath(path)
        if path not in self.__localRootCache:
            if self._IsLocalRoot(path):
                self.__localRootCache[path] = path
            elif path == '/':
                self.__localRootCache[path] = None
            else:
                self.__localRootCache[path] = self._FindLocalRoot(
                    path.rsplit('/', 1)[0])
        return self.__localRootCache[path]

    def FindLocalRoot(self, path):
        assert IsAbsolutePath(path), '{}: Absolute path expected.'.format(path)
        return self._FindLocalRoot(path)

    def CombinePaths(self, *parts):
        return CombinePaths(*parts, findLocalRootFn=self._FindLocalRoot)

    def _MakeRealPath(self, path):
        # assert IsAbsolutePath(path)
        if path == '/':
            return self.__srcRoot
        return self.__srcRoot / path[2:]

    def MakeRealPath(self, path):
        assert IsAbsolutePath(path), '{}: Absolute path expected.'.format(path)
        return self._MakeRealPath(path)

    def ReadText(self, path):
        return self.MakeRealPath(path).read_text(encoding='utf-8')
