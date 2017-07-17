#!/bin/env python3
# -*- coding: utf-8 -*-

from SrcFs import SrcFs
from Target import Target
from TargetRef import TargetRef

import io
import ninja_syntax
import os
import pathlib
import sys

import CTargets  # register subclasses

root = pathlib.Path.cwd()
builddir = root / 'pkg'
srcFs = SrcFs(root / 'src')

targets = Target.LoadTargetPlan(srcFs, (TargetRef(*arg.rsplit(':', 1))
                                        for arg in sys.argv[1:]))

transitiveDeps = dict()
for target in targets.values():
    tmp = set()
    for depRef in target.GetDeps():
        tmp.add(targets[depRef])
        tmp.update(transitiveDeps[depRef])
    transitiveDeps[target.GetTargetRef()] = frozenset(tmp)

ninjaBuffer = io.StringIO()
ninja = ninja_syntax.Writer(ninjaBuffer)

ninja.comment('x.ninja')
ninja.newline()

ninja.variable('ninja_required_version', '1.3')
ninja.newline()

ninja.variable('builddir', 'pkg')
ninja.newline()

ninja.variable('ar', 'ar')
ninja.variable('ln', 'ln -sFf')
ninja.variable('rm', 'rm -r -f')
ninja.newline()

if os.uname().sysname == 'Darwin':
    ninja.variable('cc', 'clang')
    ninja.variable('cxx', 'clang++')
    ninja.variable(
        'cc_flags',
        '-O2 -g -std=c11 -Wall -Wextra -pedantic -Werror -isystem $builddir')
    ninja.variable(
        'cxx_flags',
        '-O2 -g -std=c++14 -stdlib=libc++ -Wall -Wextra -pedantic -Werror -isystem $builddir'
    )
else:
    ninja.variable('cc', 'gcc')
    ninja.variable('cxx', 'g++')
    ninja.variable(
        'cc_flags',
        '-O2 -g -std=gnu11 -Wall -Wextra -pedantic -Werror -isystem $builddir')
    ninja.variable(
        'cxx_flags',
        '-O2 -g -std=c++14 -Wall -Wextra -pedantic -Werror -isystem $builddir')
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
    command='$ln $in $out',
    description='Creating symlink $out', )
ninja.newline()
ninja.newline()


def GenerateFakeRoot(ninja, targets):
    dirs = set()
    for _, target in sorted(targets.items()):
        for src in sorted(target.GetSrcs()):
            dirs.add(src.rsplit('/', 1)[0])
        for header in sorted(target.GetHeaders()):
            dirs.add(header.rsplit('/', 1)[0])
    fakeRootInputs = []
    for dir in sorted(dirs):
        output = '$builddir' + dir[1:] + '/@'
        fakeRootInputs.append(output)
        ninja.build(
            outputs=output,
            rule='symlink',
            inputs=str(srcFs.MakeRealPath(srcFs.FindLocalRoot(dir))), )
    for _, target in sorted(targets.items()):
        for src in sorted(target.GetSrcs()):
            output = '$builddir' + src[1:]
            fakeRootInputs.append(output)
            ninja.build(
                outputs=output,
                rule='symlink',
                inputs=str(srcFs.MakeRealPath(src)), )
        for header in sorted(target.GetHeaders()):
            output = '$builddir' + header[1:]
            fakeRootInputs.append(output)
            ninja.build(
                outputs=output,
                rule='symlink',
                inputs=str(srcFs.MakeRealPath(header)), )
    ninja.build(outputs='fake_root', rule='phony', inputs=fakeRootInputs)


GenerateFakeRoot(ninja, targets)


def cLib(targetRef):
    assert isinstance(targetRef, TargetRef)
    return '$builddir' + str(targetRef)[1:].replace(':', '/') + '.a'


def cBin(targetRef):
    assert isinstance(targetRef, TargetRef)
    return 'bin/' + targetRef.name


def cObj(src):
    return '$builddir' + src[1:] + '.o'


def cInput(src):
    return '$builddir' + src[1:]


def GenerateCLibrary(target):
    assert isinstance(target, CTargets.CLibrary)
    if not target.GetSrcs():
        # header-only
        return
    tmp = set(target.GetCompilerFlags())
    for dep in transitiveDeps[target.GetTargetRef()]:
        tmp.update(dep.GetTransitiveCompilerFlags())
    extraCompilerFlags = ' '.join(sorted(tmp))
    objs = set()
    for src in sorted(target.GetSrcs()):
        objs.add(cObj(src))
        ninja.build(
            outputs=cObj(src),
            rule='cc_compile',
            inputs=cInput(src),
            implicit='fake_root',
            variables={'extra_compiler_flags': extraCompilerFlags})
    ninja.build(
        outputs=cLib(target.GetTargetRef()), rule='ar', inputs=sorted(objs))


def GenerateCBinary(target):
    assert isinstance(target, CTargets.CBinary)
    tmp = set(target.GetCompilerFlags())
    for dep in transitiveDeps[target.GetTargetRef()]:
        tmp.update(dep.GetTransitiveCompilerFlags())
    extraCompilerFlags = ' '.join(sorted(tmp))
    tmp = set(target.GetLinkerFlags())
    for dep in transitiveDeps[target.GetTargetRef()]:
        tmp.update(dep.GetLinkerFlags())
    extraLinkerFlags = ' '.join(sorted(tmp))
    objs = set()
    for src in sorted(target.GetSrcs()):
        objs.add(cObj(src))
        ninja.build(
            outputs=cObj(src),
            rule='cc_compile',
            inputs=cInput(src),
            implicit='fake_root',
            variables={'extra_compiler_flags': extraCompilerFlags})
    for dep in transitiveDeps[target.GetTargetRef()]:
        if dep.GetSrcs():
            objs.add(cLib(dep.GetTargetRef()))
    ninja.build(
        outputs=cBin(target.GetTargetRef()),
        rule='cc_link',
        inputs=sorted(objs),
        variables={'extra_linker_flags': extraLinkerFlags})


def GenerateCxxLibrary(target):
    assert isinstance(target, CTargets.CxxLibrary)
    if not target.GetSrcs():
        # header-only
        return
    tmp = set(target.GetCompilerFlags())
    for dep in transitiveDeps[target.GetTargetRef()]:
        tmp.update(dep.GetTransitiveCompilerFlags())
    extraCompilerFlags = ' '.join(sorted(tmp))
    objs = set()
    for src in sorted(target.GetSrcs()):
        objs.add(cObj(src))
        ninja.build(
            outputs=cObj(src),
            rule='cxx_compile',
            inputs=cInput(src),
            implicit='fake_root',
            variables={'extra_compiler_flags': extraCompilerFlags})
    ninja.build(
        outputs=cLib(target.GetTargetRef()), rule='ar', inputs=sorted(objs))


def GenerateCxxBinary(target):
    assert isinstance(target, CTargets.CxxBinary)
    tmp = set(target.GetCompilerFlags())
    for dep in transitiveDeps[target.GetTargetRef()]:
        tmp.update(dep.GetTransitiveCompilerFlags())
    extraCompilerFlags = ' '.join(sorted(tmp))
    tmp = set(target.GetLinkerFlags())
    for dep in transitiveDeps[target.GetTargetRef()]:
        tmp.update(dep.GetLinkerFlags())
    extraLinkerFlags = ' '.join(sorted(tmp))
    objs = set()
    for src in sorted(target.GetSrcs()):
        objs.add(cObj(src))
        ninja.build(
            outputs=cObj(src),
            rule='cxx_compile',
            inputs=cInput(src),
            implicit='fake_root',
            variables={'extra_compiler_flags': extraCompilerFlags})
    for dep in transitiveDeps[target.GetTargetRef()]:
        if dep.GetSrcs():
            objs.add(cLib(dep.GetTargetRef()))
    ninja.build(
        outputs=cBin(target.GetTargetRef()),
        rule='cxx_link',
        inputs=sorted(objs),
        variables={'extra_linker_flags': extraLinkerFlags})


for target in targets.values():
    if isinstance(target, CTargets.CLibrary):
        GenerateCLibrary(target)
    elif isinstance(target, CTargets.CBinary):
        GenerateCBinary(target)
    elif isinstance(target, CTargets.CxxLibrary):
        GenerateCxxLibrary(target)
    elif isinstance(target, CTargets.CxxBinary):
        GenerateCxxBinary(target)
    else:
        assert False

with open('x.ninja', 'w') as fout:
    fout.write(ninjaBuffer.getvalue())
