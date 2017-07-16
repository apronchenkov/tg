# -*- coding: utf-8 -*-

import collections

_TargetRef = collections.namedtuple('TargetRef', ['path', 'name'])


class TargetRef(_TargetRef):
    __slots__ = ()

    def __str__(self):
        return '{}:{}'.format(self.path, self.name)

    def __repr__(self):
        return repr(self.__str__())
