# -*- coding: utf-8 -*-
import SrcFs

import unittest


class TestPath(unittest.TestCase):
    def test_IsName(self):
        self.assertTrue(SrcFs.IsName('xyz'))
        self.assertTrue(SrcFs.IsName('main.c'))
        self.assertTrue(SrcFs.IsName('A-b_c'))
        self.assertFalse(SrcFs.IsName(''))
        self.assertFalse(SrcFs.IsName('.'))
        self.assertFalse(SrcFs.IsName('..'))

    def test_IsRelativePath(self):
        self.assertTrue(SrcFs.IsRelativePath(''))
        self.assertTrue(SrcFs.IsRelativePath('a'))
        self.assertTrue(SrcFs.IsRelativePath('a/b/c'))
        self.assertFalse(SrcFs.IsRelativePath('a/../c'))
        self.assertFalse(SrcFs.IsRelativePath('a/../c'))
        self.assertFalse(SrcFs.IsRelativePath('/'))
        self.assertFalse(SrcFs.IsRelativePath('/a'))
        self.assertFalse(SrcFs.IsRelativePath('//a'))
        self.assertFalse(SrcFs.IsRelativePath('a/'))
        self.assertFalse(SrcFs.IsRelativePath('@/a'))

    def test_IsLocalPath(self):
        self.assertTrue(SrcFs.IsLocalPath('@'))
        self.assertTrue(SrcFs.IsLocalPath('@/a'))
        self.assertTrue(SrcFs.IsLocalPath('@/a/b/c'))
        self.assertFalse(SrcFs.IsLocalPath('@/'))
        self.assertFalse(SrcFs.IsLocalPath('@/a/../c'))
        self.assertFalse(SrcFs.IsLocalPath('@/a/../c'))
        self.assertFalse(SrcFs.IsLocalPath('@//a'))
        self.assertFalse(SrcFs.IsLocalPath('@/a/'))

    def test_IsAbsolutePath(self):
        self.assertTrue(SrcFs.IsAbsolutePath('/'))
        self.assertTrue(SrcFs.IsAbsolutePath('//a'))
        self.assertTrue(SrcFs.IsAbsolutePath('//a/b/c'))
        self.assertFalse(SrcFs.IsAbsolutePath('//'))
        self.assertFalse(SrcFs.IsAbsolutePath('//a/../c'))
        self.assertFalse(SrcFs.IsAbsolutePath('//a/../c'))
        self.assertFalse(SrcFs.IsAbsolutePath('///a'))
        self.assertFalse(SrcFs.IsAbsolutePath('//a/'))

    def test_IsPath(self):
        self.assertTrue(SrcFs.IsPath(''))
        self.assertTrue(SrcFs.IsPath('@'))
        self.assertTrue(SrcFs.IsPath('@/a'))
        self.assertTrue(SrcFs.IsPath('@/a/b/c'))
        self.assertTrue(SrcFs.IsPath('a'))
        self.assertTrue(SrcFs.IsPath('a/b/c'))
        self.assertTrue(SrcFs.IsPath('/'))
        self.assertTrue(SrcFs.IsPath('//a'))
        self.assertFalse(SrcFs.IsPath('/a'))
        self.assertFalse(SrcFs.IsPath('@/'))
        self.assertFalse(SrcFs.IsPath('@//a'))
        self.assertFalse(SrcFs.IsPath('@/a/'))
        self.assertFalse(SrcFs.IsPath('@/a/../c'))
        self.assertFalse(SrcFs.IsPath('@/a/../c'))
        self.assertFalse(SrcFs.IsPath('a/'))
        self.assertFalse(SrcFs.IsPath('a/../c'))
        self.assertFalse(SrcFs.IsPath('a/../c'))

    def test_CombinePaths(self):
        findLocalRootFn = lambda path: path.rsplit('.local', 1)[0] + '.local'
        self.assertEqual('/',
                         SrcFs.CombinePaths(
                             '/', '', '', '', findLocalRootFn=findLocalRootFn))
        self.assertEqual('//a/b.local/d/e',
                         SrcFs.CombinePaths(
                             '//a/b.local/c',
                             '',
                             '@/d',
                             'e',
                             findLocalRootFn=findLocalRootFn))
        self.assertEqual('//a/b.local/d.local/e',
                         SrcFs.CombinePaths(
                             '//a/b.local/c',
                             '',
                             '@/d.local',
                             '@/e',
                             findLocalRootFn=findLocalRootFn))
        self.assertEqual('/',
                         SrcFs.CombinePaths(
                             '//a/b.local/c',
                             '@/d',
                             'e',
                             '/',
                             findLocalRootFn=findLocalRootFn))

    # def test_read_file(self):
    #     self.assertEqual('# -*- coding: utf-8 -*-',
    #                      utils.read_file('@/targets/utils.py').split('\n')[0])

    # def test_is_target_name(self):
    #     self.assertTrue(utils.is_target_name('@:a'))
    #     self.assertTrue(utils.is_target_name('@/a/b:c'))
    #     self.assertFalse(utils.is_target_name(''))
    #     self.assertFalse(utils.is_target_name(':a'))
    #     self.assertFalse(utils.is_target_name('a/b:c'))
    #     self.assertFalse(utils.is_target_name('@/a/b:'))

    # def test_get_target_path(self):
    #     self.assertEqual('@', utils.get_target_path('@:a'))
    #     self.assertEqual('@/a/b', utils.get_target_path('@/a/b:c'))

    # def test_get_target_shortname(self):
    #     self.assertEqual('a', utils.get_target_shortname('@:a'))
    #     self.assertEqual('c', utils.get_target_shortname('@/a/b:c'))

    # def test_unique(self):
    #     self.assertEqual([], utils.unique([]))
    #     self.assertEqual([1, 2, 3], utils.unique([1, 2, 3]))
    #     self.assertEqual([3, 1, 2], utils.unique([3, 1, 2, 3, 2, 1]))

    # def test_unique_last(self):
    #     self.assertEqual([], utils.unique_last([]))
    #     self.assertEqual([1, 2, 3], utils.unique_last([1, 2, 3]))
    #     self.assertEqual([3, 2, 1], utils.unique_last([3, 1, 2, 3, 2, 1]))


if __name__ == '__main__':
    unittest.main()
