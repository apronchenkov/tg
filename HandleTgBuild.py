# -*- coding: utf-8 -*-

import os
import io
import ninja_syntax
import pathlib
import sys
import subprocess

import CTargets
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


def cLib(targetRef):
    assert isinstance(targetRef, TargetRef)
    return 'pkg' + str(targetRef)[1:].replace(':', '/') + '.a'


def cBin(targetRef):
    assert isinstance(targetRef, TargetRef)
    return 'bin/' + targetRef.name


def cObj(src):
    return 'pkg' + src[1:] + '.o'


def cInput(src):
    return 'pkg' + src[1:]


def GenerateCLibrary(target, transitiveDeps, ninja):
    assert isinstance(target, CTargets.CLibrary)
    if not target.GetSrcs():
        # header-only
        return
    tmp = set(target.GetCompilerFlags())
    for dep in transitiveDeps:
        tmp.update(dep.GetTransitiveCompilerFlags())
    extraCompilerFlags = ' '.join(sorted(tmp))
    objs = set()
    for src in sorted(target.GetSrcs()):
        objs.add(cObj(src))
        ninja.build(
            outputs=cObj(src),
            rule='cc_compile',
            inputs=cInput(src),
            order_only=['build.ninja', 'fake_root'],
            variables={'extra_compiler_flags': extraCompilerFlags})
    ninja.build(
        outputs=cLib(target.GetTargetRef()), rule='ar', inputs=sorted(objs))
    ninja.newline()


def GenerateCBinary(target, transitiveDeps, ninja):
    assert isinstance(target, CTargets.CBinary)
    tmp = set(target.GetCompilerFlags())
    for dep in transitiveDeps:
        tmp.update(dep.GetTransitiveCompilerFlags())
    extraCompilerFlags = ' '.join(sorted(tmp))
    tmp = set(target.GetLinkerFlags())
    for dep in transitiveDeps:
        tmp.update(dep.GetLinkerFlags())
    extraLinkerFlags = ' '.join(sorted(tmp))
    objs = set()
    for src in sorted(target.GetSrcs()):
        objs.add(cObj(src))
        ninja.build(
            outputs=cObj(src),
            rule='cc_compile',
            inputs=cInput(src),
            order_only=['build.ninja', 'fake_root'],
            variables={'extra_compiler_flags': extraCompilerFlags})
    for dep in transitiveDeps:
        if dep.GetSrcs():
            objs.add(cLib(dep.GetTargetRef()))
    ninja.build(
        outputs=cBin(target.GetTargetRef()),
        rule='cc_link',
        inputs=sorted(objs),
        variables={'extra_linker_flags': extraLinkerFlags})
    ninja.newline()


def GenerateCxxLibrary(target, transitiveDeps, ninja):
    assert isinstance(target, CTargets.CxxLibrary)
    if not target.GetSrcs():
        # header-only
        return
    tmp = set(target.GetCompilerFlags())
    for dep in transitiveDeps:
        tmp.update(dep.GetTransitiveCompilerFlags())
    extraCompilerFlags = ' '.join(sorted(tmp))
    objs = set()
    for src in sorted(target.GetSrcs()):
        objs.add(cObj(src))
        ninja.build(
            outputs=cObj(src),
            rule='cxx_compile',
            inputs=cInput(src),
            order_only=['build.ninja', 'fake_root'],
            variables={'extra_compiler_flags': extraCompilerFlags})
    ninja.build(
        outputs=cLib(target.GetTargetRef()), rule='ar', inputs=sorted(objs))
    ninja.newline()


def GenerateCxxBinary(target, transitiveDeps, ninja):
    assert isinstance(target, CTargets.CxxBinary)
    tmp = set(target.GetCompilerFlags())
    for dep in transitiveDeps:
        tmp.update(dep.GetTransitiveCompilerFlags())
    extraCompilerFlags = ' '.join(sorted(tmp))
    tmp = set(target.GetLinkerFlags())
    for dep in transitiveDeps:
        tmp.update(dep.GetLinkerFlags())
    extraLinkerFlags = ' '.join(sorted(tmp))
    objs = set()
    for src in sorted(target.GetSrcs()):
        objs.add(cObj(src))
        ninja.build(
            outputs=cObj(src),
            rule='cxx_compile',
            inputs=cInput(src),
            order_only=['build.ninja', 'fake_root'],
            variables={'extra_compiler_flags': extraCompilerFlags})
    for dep in transitiveDeps:
        if dep.GetSrcs():
            objs.add(cLib(dep.GetTargetRef()))
    ninja.build(
        outputs=cBin(target.GetTargetRef()),
        rule='cxx_link',
        inputs=sorted(objs),
        variables={'extra_linker_flags': extraLinkerFlags})
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
    ninja.variable('ln', 'ln -sFf')
    ninja.variable('rm', 'rm -r -f')
    ninja.variable('tg', 'tg')
    ninja.newline()

    if os.uname().sysname == 'Darwin':
        ninja.variable('cc', 'clang')
        ninja.variable('cxx', 'clang++')
        ninja.variable(
            'cc_flags',
            '-O2 -g -std=c11 -Wall -Wextra -pedantic -Werror -isystem pkg')
        ninja.variable(
            'cxx_flags',
            '-O2 -g -std=c++14 -stdlib=libc++ -Wall -Wextra -pedantic -Werror -isystem pkg'
        )
    else:
        ninja.variable('cc', 'gcc')
        ninja.variable('cxx', 'g++')
        ninja.variable(
            'cc_flags',
            '-O2 -g -std=gnu11 -Wall -Wextra -pedantic -Werror -isystem pkg')
        ninja.variable(
            'cxx_flags',
            '-O2 -g -std=c++14 -Wall -Wextra -pedantic -Werror -isystem pkg')
    ninja.newline()

    ninja.rule(
        name='cc_compile',
        command=
        '$cc $cc_flags -MMD -MT $out -MF $out.d -c $in -o $out $extra_compiler_flags',
        description='Building C file $in',
        depfile='$out.d',
        deps='gcc')
    ninja.newline()

    ninja.rule(
        name='cc_link',
        command='$cc $cc_flags $in -o $out $extra_linker_flags',
        description='Linking $out', )
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
        tmp = set()
        for depRef in target.GetDeps():
            tmp.add(targetPlan[depRef])
            tmp.update(transitiveDepsDict[depRef])
        transitiveDepsDict[target.GetTargetRef()] = tmp

    for targetRef, target in targetPlan.items():
        if isinstance(target, CTargets.CLibrary):
            GenerateCLibrary(target, transitiveDepsDict[targetRef], ninja)
        elif isinstance(target, CTargets.CBinary):
            GenerateCBinary(target, transitiveDepsDict[targetRef], ninja)
        elif isinstance(target, CTargets.CxxLibrary):
            GenerateCxxLibrary(target, transitiveDepsDict[targetRef], ninja)
        elif isinstance(target, CTargets.CxxBinary):
            GenerateCxxBinary(target, transitiveDepsDict[targetRef], ninja)
        else:
            assert False

    return MakeToken(targetRefs) + '\n' + ninjaBuffer.getvalue()


def ValidateBuildNinjaToken(tgPath, targetRefs):
    buildNinjaPath = tgPath / 'build.ninja'
    if not buildNinjaPath.exists():
        return False
    with buildNinjaPath.open('r', encoding='utf-8') as istream:
        return istream.readline().strip() == MakeToken(targetRefs)


def HandleTgBuild(tgPath, args):
    # init
    srcPath = tgPath / 'src'
    srcFs = SrcFs(srcPath)
    # currentPath
    cwd = pathlib.Path.cwd()
    if srcPath == cwd:
        currentPath = '/'
    elif srcPath in cwd.parents:
        currentPath = '//' + str(cwd.relative_to(srcPath))
    else:
        currentPath = None
    # targetRefs
    ninjaTrainingMode = False
    targetRefs = set()
    for arg in args:
        if arg == kFlagNinjaTraining:
            ninjaTrainingMode = True
            continue
        tokens = arg.rsplit(':', 1)
        assert len(tokens) == 2 and srcFs.IsPath(tokens[0]) and srcFs.IsName(
            tokens[1]), '{}: Invalid target.'.format(arg)
        if srcFs.IsAbsolutePath(tokens[0]):
            targetRefs.add(TargetRef(path=tokens[0], name=tokens[1]))
        else:
            assert currentPath is not None, '{}: Unable to find target.'.format(
                token[0])
            targetRefs.add(
                TargetRef(
                    path=srcFs.CombinePaths(currentPath, tokens[0]),
                    name=tokens[1]))
    targetRefs = tuple(sorted(targetRefs))
    assert targetRefs, "tg build: List of targets is expected."
    # Ninja training
    if ninjaTrainingMode or not ValidateBuildNinjaToken(tgPath, targetRefs):
        targetCache = TargetCache(srcFs)
        with (tgPath / 'build.ninja').open('w', encoding='utf-8') as ostream:
            ostream.write(
                MakeBuildNinja(tgPath, srcFs, targetRefs,
                               targetCache.MakeTargetPlan(targetRefs)))
    if not ninjaTrainingMode:
        sys.exit(subprocess.call(['ninja', '-C', str(tgPath)]))
