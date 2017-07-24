# -*- coding: utf-8 -*-

import collections
from Target import Target


class TargetCache:
    def __init__(self, srcFs):
        self.__srcFs = srcFs
        self.__loadedPaths = dict()

    def GetSrcFs(self):
        return self.__srcFs

    def GetTargets(self, path):
        assert self.__srcFs.IsAbsolutePath(
            path), '{}: Absolute path expected.'.format(path)
        if path not in self.__loadedPaths:
            self.__loadedPaths[path] = Target.LoadTargets(self.__srcFs, path)
        return self.__loadedPaths[path]

    def GetTarget(self, targetRef):
        result = self.GetTargets(targetRef.path).get(targetRef)
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
