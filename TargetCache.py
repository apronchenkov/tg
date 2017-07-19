# -*- coding: utf-8 -*-

import collections
from Target import Target


class TargetCache:
    def __init__(self, srcFs):
        self.__srcFs = srcFs
        self.__loadedPaths = set()
        self.__loadedTargets = dict()

    def GetTarget(self, targetRef):
        if targetRef.path not in self.__loadedPaths:
            self.__loadedTargets.update(
                Target.LoadTargets(self.__srcFs, targetRef.path))
            self.__loadedPaths.add(targetRef.path)
        result = self.__loadedTargets.get(targetRef)
        assert result, '{}: Missing target.'.format(targetRef)
        return result

    def MakeTargetPlan(self, targetRefs):
        result = collections.OrderedDict()
        stack = list(targetRefs)
        visited = set()
        charged = set()
        while stack:
            targetRef = stack.pop()
            target = self.GetTarget(targetRef)
            if targetRef in charged:
                charged.remove(targetRef)
                result[targetRef] = target
                continue
            if targetRef in visited:
                continue
            visited.add(targetRef)
            charged.add(targetRef)
            stack.append(targetRef)
            for depRef in target.GetDeps():
                assert depRef not in charged, '{PARENT} -> ... -> {CHILD} -> {PARENT}: Circular dependency.'.format(
                    PARENT=depRef, CHILD=targetRef)
                stack.append(depRef)
        return result
