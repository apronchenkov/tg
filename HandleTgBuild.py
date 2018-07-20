# -*- coding: utf-8 -*-

import os
import io
import ninja_syntax
import pathlib
import sys
import subprocess

import CCTargets
from SrcFs import SrcFs
from TargetCache import TargetCache
from TargetRef import TargetRef

kFlagNinjaTraining = '--ninja-training'


def MakeToken(targetRefs):
    return '# tg ' + ' '.join(str(targetRef) for targetRef in targetRefs)


def GenerateFakeRoot(srcFs, targets, ninja):
    symlinks = set()

    def generateSymlink(inputPath, outputPath):
        ninja.build(
            outputs=outputPath,
            rule='symlink',
            variables={
                'relpath_in':
                os.path.relpath(inputPath, os.path.dirname(outputPath))
            },
            order_only='build.ninja')
        symlinks.add(outputPath)

    dirs = set()
    for _, target in sorted(targets.items()):
        for src in sorted(target.GetSrcs()):
            dirs.add(src.rsplit('/', 1)[0])
        for header in sorted(target.GetHeaders()):
            dirs.add(header.rsplit('/', 1)[0])

    for dir in sorted(dirs):
        generateSymlink('pkg' + srcFs.FindLocalRoot(dir)[1:],
                        'pkg' + dir[1:] + '/@')
    for _, target in sorted(targets.items()):
        for src in sorted(target.GetSrcs()):
            generateSymlink(
                'src' + src[1:],
                'pkg' + src[1:], )
        for header in sorted(target.GetHeaders()):
            generateSymlink(
                'src' + header[1:],
                'pkg' + header[1:], )
    ninja.build(outputs='fake_root', rule='phony', inputs=sorted(symlinks))
    ninja.newline()


def IsCFile(src):
    return src.endswith('.c')


def IsCxxFile(src):
    return src.endswith('.cpp') or src.endswith('.cc')


def IsHeaderFile(src):
    return src.endswith('.h') or src.endswith('.hh')


def ccLib(targetRef):
    assert isinstance(targetRef, TargetRef)
    return 'pkg' + str(targetRef)[1:].replace(':', '/') + '.a'


def ccBin(targetRef):
    assert isinstance(targetRef, TargetRef)
    return 'bin' + str(targetRef)[1:].replace(':', '/')


def ccBinSymlink(targetRef):
    assert isinstance(targetRef, TargetRef)
    return 'src' + str(targetRef)[1:].replace(':', '/')


def ccObj(src):
    assert IsCFile(src) or IsCxxFile(src)
    return 'pkg' + src[1:] + '.o'


def ccInput(src):
    return 'pkg' + src[1:]


def GenerateCCLibrary(target, transitiveDeps, ninja):
    assert isinstance(target, CCTargets.CCLibrary)
    compilerVariables = {}
    tmp = set(target.GetCompilerFlags())
    tmp.update(target.GetTransitiveCompilerFlags())
    for dep in transitiveDeps:
        tmp.update(dep.GetTransitiveCompilerFlags())
    if tmp:
        compilerVariables['extra_compiler_flags'] = ' '.join(sorted(tmp))
    objs = set()
    for src in sorted(target.GetSrcs()):
        if IsHeaderFile(src):
            continue
        elif IsCFile(src):
            compilerRule = 'c_compile'
        elif IsCxxFile(src):
            compilerRule = 'cxx_compile'
        else:
            raise RuntimeError('Unexpected file extension: ' + src)
        objs.add(ccObj(src))
        ninja.build(
            outputs=ccObj(src),
            rule=compilerRule,
            inputs=ccInput(src),
            order_only=['build.ninja', 'fake_root'],
            variables=compilerVariables)
    if objs:
        ninja.build(
            outputs=ccLib(target.GetTargetRef()),
            rule='ar',
            inputs=sorted(objs))
        ninja.newline()


def GenerateCCBinary(target, transitiveDeps, ninja):
    assert isinstance(target, CCTargets.CCBinary)
    compilerVariables = {}
    tmp = set(target.GetCompilerFlags())
    tmp.update(target.GetTransitiveCompilerFlags())
    for dep in transitiveDeps:
        tmp.update(dep.GetTransitiveCompilerFlags())
    if tmp:
        compilerVariables['extra_compiler_flags'] = ' '.join(sorted(tmp))
    linkerVariables = {}
    tmp = set(target.GetLinkerFlags())
    for dep in transitiveDeps:
        tmp.update(dep.GetLinkerFlags())
    if tmp:
        linkerVariables['extra_linker_flags'] = ' '.join(sorted(tmp))
    objs = set()
    for src in sorted(target.GetSrcs()):
        if IsHeaderFile(src):
            continue
        elif IsCFile(src):
            compilerRule = 'c_compile'
        elif IsCxxFile(src):
            compilerRule = 'cxx_compile'
        else:
            raise RuntimeError('Unexpected file extension: ' + src)
        objs.add(ccObj(src))
        ninja.build(
            outputs=ccObj(src),
            rule=compilerRule,
            inputs=ccInput(src),
            order_only=['build.ninja', 'fake_root'],
            variables=compilerVariables)
    objs = sorted(objs)
    for dep in transitiveDeps:
        if dep.GetSrcs():
            objs.append(ccLib(dep.GetTargetRef()))
    ninja.build(
        outputs=ccBin(target.GetTargetRef()),
        rule='cxx_link',
        inputs=objs,
        variables=linkerVariables)
    ninja.build(
        outputs=ccBinSymlink(target.GetTargetRef()),
        rule='symlink',
        variables={
            'relpath_in':
            os.path.relpath(
                ccBin(target.GetTargetRef()),
                os.path.dirname(ccBinSymlink(target.GetTargetRef())))
        }, )
    ninja.newline()


def MakeBuildNinja(tgPath, srcFs, targetRefs, targetPlan):
    ninjaBuffer = io.StringIO()
    ninja = ninja_syntax.Writer(ninjaBuffer)
    ninja.comment('build.ninja')
    ninja.newline()

    ninja.variable('ninja_required_version', '1.3')
    ninja.newline()

    ninja.variable('builddir', '.')
    ninja.newline()

    ninja.variable('ar', 'ar')
    ninja.variable('ln', 'ln -snf')
    ninja.variable('rm', 'rm -r -f')
    ninja.variable('tg', 'tg')
    ninja.newline()

    ccFlags = [
        '-O2',
        '-g',
        '-march=native',
        '-Wall',
        '-Wextra',
        '-pedantic',
        '-Werror',
        '-isystem pkg',
        '-pthread',
    ]
    if os.uname().sysname == 'Darwin':
        ninja.variable('cc', 'clang')
        ninja.variable('cxx', 'clang++')
        ninja.variable('cc_flags', ccFlags + ['-std=c11'])
        ninja.variable('cxx_flags', ccFlags + ['-std=c++17', '-stdlib=libc++'])
    else:
        ninja.variable('cc', 'gcc')
        ninja.variable('cxx', 'g++')
        ninja.variable('cc_flags', ccFlags + ['-std=gnu11', '-mcpu=native'])
        ninja.variable('cxx_flags', ccFlags + ['-std=c++17', '-mcpu=native'])
    ninja.newline()

    ninja.rule(
        name='c_compile',
        command=
        '$cc $cc_flags -MMD -MT $out -MF $out.d -c $in -o $out $extra_compiler_flags',
        description='Building C file $in',
        depfile='$out.d',
        deps='gcc')
    ninja.newline()

    ninja.rule(
        name='cxx_compile',
        command=
        '$cxx $cxx_flags -MMD -MT $out -MF $out.d -c $in -o $out $extra_compiler_flags',
        description='Building C++ file $in',
        depfile='$out.d',
        deps='gcc')
    ninja.newline()

    ninja.rule(
        name='cxx_link',
        command='$cxx $cxx_flags $in -o $out $extra_linker_flags',
        description='Linking $out', )
    ninja.newline()

    ninja.rule(
        name='ar',
        command='$rm $out && $ar crs $out $in',
        description='Creating archive $out', )
    ninja.newline()

    ninja.rule(
        name='symlink',
        command='$ln $relpath_in $out',
        description='Creating symlink $out', )
    ninja.newline()
    ninja.newline()

    ninja.rule(
        name='rebuild_ninja',
        command='$tg build {} $target_refs'.format(kFlagNinjaTraining),
        description='Ninja training')
    ninja.newline()

    ninja.build(
        outputs=[
            'build.ninja',
        ],
        rule='rebuild_ninja',
        variables={
            'target_refs': [str(targetRef) for targetRef in targetRefs],
        },
        implicit=sorted(
            set(
                str(
                    srcFs.MakeRealPath(targetRef.path).relative_to(tgPath) /
                    'TARGETS') for targetRef in targetPlan.keys())))
    ninja.newline()

    GenerateFakeRoot(srcFs, targetPlan, ninja)

    transitiveDepsDict = dict()
    for target in targetPlan.values():
        transitiveDeps = []
        for depRef in target.GetDeps():
            transitiveDeps.append(targetPlan[depRef])
            transitiveDeps.extend(transitiveDepsDict[depRef])
        # preserve only the latest entrance of each dependency
        visited = set()
        tmp = []
        for dep in reversed(transitiveDeps):
            if dep.GetTargetRef() not in visited:
                visited.add(dep.GetTargetRef())
                tmp.append(dep)
        transitiveDepsDict[target.GetTargetRef()] = list(reversed(tmp))

    for targetRef, target in targetPlan.items():
        if isinstance(target, CCTargets.CCLibrary):
            GenerateCCLibrary(target, transitiveDepsDict[targetRef], ninja)
        elif isinstance(target, CCTargets.CCBinary):
            GenerateCCBinary(target, transitiveDepsDict[targetRef], ninja)
        else:
            assert False

    return MakeToken(targetRefs) + '\n' + ninjaBuffer.getvalue()


def ValidateBuildNinjaToken(tgPath, targetRefs):
    buildNinjaPath = tgPath / 'build.ninja'
    if not buildNinjaPath.exists():
        return False
    with buildNinjaPath.open('r', encoding='utf-8') as istream:
        return istream.readline().strip() == MakeToken(targetRefs)


def ListTargets(targetCache, pattern):
    # currentPath
    srcFs = targetCache.GetSrcFs()
    srcFsRoot = srcFs.GetRealSrcRoot()
    cwd = pathlib.Path.cwd()
    currentPath = None
    if srcFsRoot == cwd or srcFsRoot in cwd.parents:
        currentPath = srcFs.MakePath(cwd)
    # parse pattern
    path = None
    name = None
    tokens = pattern.rsplit(':', 1)
    if len(tokens) == 2:
        path = tokens[0]
        name = tokens[1]
    elif pattern == '.':
        path = ''
    else:
        path = pattern
    assert srcFs.IsPath(path), '{}: Invalid target.'.format(pattern)
    assert not name or srcFs.IsName(name), '{}: Invalid target.'.format(
        pattern)
    if not srcFs.IsAbsolutePath(path):
        assert currentPath is not None, '{}: Unable to find target.'.format(
            pattern)
        path = srcFs.CombinePaths(currentPath, path)
    result = []
    if name:
        result.append(TargetRef(path=path, name=name))
    else:
        for realPath in srcFs.MakeRealPath(path).rglob('TARGETS'):
            if realPath.is_file():
                result.extend(
                    targetCache.GetTargets(srcFs.MakePath(realPath.parent))
                    .keys())
    return result


def HandleTgBuild(tgPath, args):
    srcFs = SrcFs(tgPath / 'src')
    targetCache = TargetCache(srcFs)
    ninjaTrainingMode = False
    targetRefs = set()
    for arg in args:
        if arg == kFlagNinjaTraining:
            ninjaTrainingMode = True
            continue
        targetRefs.update(ListTargets(targetCache, arg))
    targetRefs = tuple(sorted(targetRefs))
    assert targetRefs, "tg build: List of targets is expected."
    # Ninja training
    if ninjaTrainingMode or not ValidateBuildNinjaToken(tgPath, targetRefs):
        with (tgPath / 'build.ninja').open('w', encoding='utf-8') as ostream:
            ostream.write(
                MakeBuildNinja(tgPath, srcFs, targetRefs,
                               targetCache.MakeTargetPlan(targetRefs)))
    if not ninjaTrainingMode:
        sys.exit(subprocess.call(['ninja', '-C', str(tgPath)]))
