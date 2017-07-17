from Target import Target


class CTarget(Target):
    def __init__(
            self,
            srcFs,
            path,
            name,
            deps=tuple(),
            srcs=tuple(),
            headers=tuple(),
            compiler_flags=tuple(),
            transitive_compiler_flags=tuple(),
            linker_flags=tuple(), ):
        super().__init__(srcFs, path, name, deps)
        normalizedSrcs = []
        for src in srcs:
            assert src and srcFs.IsRelativePath(
                src), '{}:{}: {}: Invalid src.'.format(path, name, src)
            normalizedSrcs.append(srcFs.CombinePaths(path, src))
        self.__srcs = frozenset(normalizedSrcs)
        normalizedHeaders = []
        for header in headers:
            assert header and srcFs.IsRelativePath(
                header), '{}:{}: {}: Invalid header.'.format(
                    path, name, header)
            normalizedHeaders.append(srcFs.CombinePaths(path, header))
        self.__headers = frozenset(normalizedHeaders)
        for compilerFlag in compiler_flags:
            assert compilerFlag and isinstance(
                compilerFlag, str), '{}:{}: {}: Invalid compiler flag.'.format(
                    path, name, compilerFlag)
        self.__compilerFlags = frozenset(compiler_flags)
        for compilerFlag in transitive_compiler_flags:
            assert compilerFlag and isinstance(
                compilerFlag,
                str), '{}:{}: {}: Invalid transitive compiler flag.'.format(
                    path, name, compilerFlag)
        self.__transitiveCompilerFlags = frozenset(transitive_compiler_flags)
        for linkerFlag in linker_flags:
            assert linkerFlag and isinstance(
                linkerFlag, str), '{}:{}: {}: Invalid linker flag.'.format(
                    path, name, linkerFlag)
        self.__linkerFlags = frozenset(linker_flags)

    def GetSrcs(self):
        return self.__srcs

    def GetHeaders(self):
        return self.__headers

    def GetCompilerFlags(self):
        return self.__compilerFlags

    def GetLinkerFlags(self):
        return self.__linkerFlags

    def GetTransitiveCompilerFlags(self):
        return self.__transitiveCompilerFlags

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        result = ""
        result += "{}(\n".format(self.__class__.publicName)
        result += "  name = {},\n".format(repr(self.GetTargetRef()))
        srcs = self.GetSrcs()
        if srcs:
            result += "  srcs = [\n"
            for src in sorted(srcs):
                result += "    {},\n".format(repr(src))
            result += "  ],\n"
        headers = self.GetHeaders()
        if headers:
            result += "  headers = [\n"
            for header in sorted(headers):
                result += "    {},\n".format(repr(header))
            result += "  ],\n"
        compilerFlags = self.GetCompilerFlags()
        if compilerFlags:
            result += "  compiler_flags = [\n"
            for compilerFlag in sorted(compilerFlags):
                result += "    {},\n".format(repr(compilerFlag))
            result += "  ],\n"
        transitiveCompilerFlags = self.GetTransitiveCompilerFlags()
        if transitiveCompilerFlags:
            result += "  transitive_compiler_flags = [\n"
            for compilerFlag in sorted(transitiveCompilerFlags):
                result += "    {},\n".format(repr(compilerFlag))
            result += "  ],\n"
        linkerFlags = self.GetLinkerFlags()
        if linkerFlags:
            result += "  linker_flags = [\n"
            for linkerFlag in sorted(linkerFlags):
                result += "    {},\n".format(repr(linkerFlag))
            result += "  ],\n"
        deps = self.GetDeps()
        if deps:
            result += "  deps = [\n"
            for dep in sorted(self.GetDeps()):
                result += "    {},\n".format(repr(dep))
            result += "  ],\n"
        result += ")"
        return result


class CLibrary(CTarget):
    publicName = 'c_library'


class CBinary(CTarget):
    publicName = 'c_binary'


class CxxLibrary(CTarget):
    publicName = 'cxx_library'


class CxxBinary(CTarget):
    publicName = 'cxx_binary'
