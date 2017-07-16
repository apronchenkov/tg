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

targetRefs = [TargetRef(*arg.rsplit(':', 1)) for arg in sys.argv[1:]]

targets = Target.LoadTargetPlan(srcFs, targetRefs)

ninjaBuffer = io.StringIO()
ninja = ninja_syntax.Writer(ninjaBuffer)

ninja.comment('x.ninja')
ninja.newline()

ninja.variable('ninja_required_version', '1.3')
ninja.newline()

ninja.variable('builddir', 'pkg')
ninja.newline()

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


def generateFakeRoot(ninja, targets):
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


generateFakeRoot(ninja, targets)

#print(ninjaBuffer.getvalue())

with open('x.ninja', 'w') as fout:
    fout.write(ninjaBuffer.getvalue())
