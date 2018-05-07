# -*- coding: utf-8 -*-

from TargetRef import TargetRef

import collections

kTargetsFile = 'TARGETS'


class Target:
    def __init__(self, srcFs, path, name, deps):
        assert srcFs.IsAbsolutePath(path)
        assert srcFs.IsName(name)
        self.__targetRef = TargetRef(path=path, name=name)
        normalizedDeps = set()
        for dep in deps:
            depTokens = dep.rsplit(':')
            assert (len(depTokens) == 2 and srcFs.IsPath(depTokens[0]) and
                    srcFs.IsName(depTokens[1])
                    ), path + ':' + name + ': ' + dep + ': Invalid dependency.'
            normalizedDeps.add(
                TargetRef(
                    path=srcFs.CombinePaths(path, depTokens[0]),
                    name=depTokens[1]))
        self.__deps = tuple(sorted(normalizedDeps))

    def GetTargetRef(self):
        return self.__targetRef

    def GetDeps(self):
        return self.__deps

    @classmethod
    def LoadTargets(clazz, srcFs, path):
        assert srcFs.IsAbsolutePath(path)
        publicGlobals = dict()
        targets = []

        def makeTargetClassBinding(targets, subclazz, srcFs, path):
            return lambda **kwargs: targets.append(subclazz(srcFs, path, **kwargs))

        def scanTargetClasses(clazz):
            for subclazz in clazz.__subclasses__():
                publicName = getattr(subclazz, 'publicName', None)
                if publicName is not None and publicName not in publicGlobals:
                    publicGlobals[publicName] = makeTargetClassBinding(
                        targets, subclazz, srcFs, path)
                scanTargetClasses(subclazz)

        scanTargetClasses(Target)
        targetsPath = srcFs.CombinePaths(path, kTargetsFile)
        exec(
            compile(
                srcFs.ReadText(targetsPath),
                str(srcFs.MakeRealPath(targetsPath)), 'exec'), publicGlobals,
            {})

        result = dict()
        for target in targets:
            assert target.GetTargetRef(
            ) not in result, '{}: Mutiple targets with the same name.'.format(
                target.GetTargetRef())
            result[target.GetTargetRef()] = target
        return result

    @classmethod
    def LoadTargetPlan(clazz, srcFs, targetRefs):
        result = collections.OrderedDict()

        class MissingTarget(Exception):
            def __init__(self, missingTargetRef):
                self.missingTargetRef = missingTargetRef

        class CirtularDependency(Exception):
            def __init__(self, parentTargetRef, childTargetRef):
                self.parentTargetRef = parentTargetRef
                self.childTargetRef = childTargetRef

        loadedTargetPaths = set()
        targetDict = dict()

        def getTarget(targetRef):
            if targetRef.path not in loadedTargetPaths:
                loadedTargetPaths.add(targetRef.path)
                targetDict.update(Target.LoadTargets(srcFs, targetRef.path))
            target = targetDict.get(targetRef)
            if target:
                return target
            raise MissingTarget(targetRef)

        inProgressSet = set()
        visitedSet = set()

        def dfs(targetRef):
            target = getTarget(targetRef)
            inProgressSet.add(targetRef)
            for depRef in target.GetDeps():
                if depRef in inProgressSet:
                    raise CirtularDependency(targetRef)
                if depRef in visitedSet:
                    continue
                visitedSet.add(depRef)
                dfs(depRef)
            inProgressSet.remove(targetRef)
            result[targetRef] = target

        try:
            for targetRef in targetRefs:
                dfs(targetRef)
        except MissingTarget as ex:
            raise AssertError(
                '{}: Target not found.'.format(ex.missingTargetRef))
        except CirtularDependency as ex:
            raise AssertError(
                '{PARENT} -> ... -> {CHILD} -> {PARENT}: Circular dependency.'.
                format(PARENT=ex.parentTargetRef, CHILD=ex.childTargetRef))
        return result
