#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
文件处理工具模块

@module file_tool
@file file_tool.py

"""

import sys
import os
import re
import platform
import subprocess
import shutil

__MOUDLE__ = 'file_tool'  # 模块名
__DESCRIPT__ = u'文件处理工具'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.08.29'  # 发布日期


class FileTool(object):
    """
    文件处理工具
    提供各类文件、目录相关的常用工具函数（静态方法）

    """

    @staticmethod
    def get_exefile_fullname():
        """
        获得执行主程序文件名（含路径）

        @returns {string} - 执行主程序文件名（含路径）

        @example
            filepath = FileTool.get_exefile_fullname()

        """
        return os.path.realpath(sys.argv[0])

    @staticmethod
    def get_exefile_name():
        """
        获得执行主程序文件名（不含路径，含扩展名）

        @returns {string} - 文件名（不含路径，含扩展名）

        @example
            filepath = FileTool.get_exefile_name()

        """
        return os.path.split(os.path.realpath(sys.argv[0]))[1]

    @staticmethod
    def get_exefile_name_no_ext():
        """
        获得执行主程序文件名（不含路径，不含扩展名）

        @returns {string} - 文件名（不含路径，不含扩展名）

        @example
            filepath = FileTool.get_exefile_name_no_ext()

        """
        _filename = os.path.split(os.path.realpath(sys.argv[0]))[1]
        _dot_index = _filename.rfind(".")
        if _dot_index == -1:
            return _filename
        else:
            return _filename[0: _dot_index]

    @staticmethod
    def get_exefile_path():
        """
        获得执行主程序的路径（不含文件名）

        @returns {string} - 程序路径（不含文件名，最后一个字符不为路径分隔符）

        @example
            filepath = FileTool.get_exefile_path()

        """
        return os.path.split(os.path.realpath(sys.argv[0]))[0]

    @staticmethod
    def get_dir_name(path):
        """
        获取指定目录的目录名

        @param {string} path - 要获取的目录路径

        @returns {string} - 目录名

        """
        _path = os.path.split(os.path.realpath(path))[0].rstrip('\\/').replace('\\', '/')
        _index = _path.rfind('/')
        if _index >= 0:
            return _path[_index + 1:]

        return _path

    @staticmethod
    def create_dir(path):
        """
        创建指定的路径

        @param {string} path - 需要创建的路径

        @throws {FileExistsError} - 路径存在的情况抛出文件存在异常

        @example
            FileTool.create_dir("c:/test/")

        """
        os.makedirs(path)

    @staticmethod
    def get_filelist(path='', regex_str='', is_fullname=True):
        """
        获取指定目录下的文件清单

        @param {string} path='' - 需要获取文件的目录
        @param {string} regex_str='' - 需匹配文件名的正则表达式（''代表无需匹配）
        @param {bool} is_fullname=True - 结果的文件名是否包含路径

        @returns {string[]} - 文件清单数组

        @example
            filelist = FileTools.get_filelist(path='c:\\')

        """
        _filelist = []
        _file_names = os.listdir(path)
        _pattern = None
        if len(regex_str) > 0:
            _pattern = re.compile(regex_str)
        for fn in _file_names:
            _full_filename = os.path.join(path, fn)
            if os.path.isfile(_full_filename):
                _temp_filename = fn
                if is_fullname:
                    _temp_filename = _full_filename
                if _pattern is not None:
                    if _pattern.match(fn):
                        _filelist.append(_temp_filename)
                else:
                    _filelist.append(_temp_filename)
        return _filelist

    @staticmethod
    def get_dirlist(path='', regex_str='', is_fullpath=True):
        """
        获取指定目录下的子目录清单

        @param {string} path='' - 需要获取子目录的目录
        @param {string} regex_str='' - 需匹配目录名的正则表达式（''代表无需匹配）
        @param {bool} is_fullpath=True - 结果的目录名是否包含路径

        @returns {string[]} - 目录清单数组（不带最后的分隔符）

        @throws {FileNotFoundError} - 当path不存在的情况下，会抛出该异常

        """
        _dirlist = []
        _file_names = os.listdir(path)
        _pattern = None
        if regex_str != "":
            _pattern = re.compile(regex_str)
        for fn in _file_names:
            _full_filename = os.path.join(path, fn)
            if not os.path.isfile(_full_filename):
                _temp_filename = fn
                if is_fullpath:
                    _temp_filename = _full_filename
                if _pattern is not None:
                    if _pattern.match(fn):
                        _dirlist.append(_temp_filename)
                else:
                    _dirlist.append(_temp_filename)
        return _dirlist

    @staticmethod
    def remove_dir(path):
        """
        删除指定目录（及目录下的所有文件及目录）
        由于Windows平台在处理删除目录时会存在一些权限异常，因此采用命令执行方式删除

        @param {string} path - 要删除的目录

        @throws {FileNotFoundError} - 找不到指定的路径时抛出该异常
        @throws {PermissionError} - 没有权限时抛出该异常
        @throws {NotADirectoryError} - 如果给出的路径不是目录而是文件时抛出

        """
        if platform.system() == 'Windows':
            real_path = os.path.realpath(path)
            if not os.path.exists(real_path):
                raise FileNotFoundError
            elif os.path.isfile(real_path):
                raise NotADirectoryError
            if subprocess.run('rmdir /S /Q %s' % (real_path.replace('/', '\\')), shell=True).returncode != 0:
                raise PermissionError
        else:
            shutil.rmtree(path=path, ignore_errors=False)

    @staticmethod
    def remove_file(filename):
        """
        删除指定文件

        @param {string} filename - 需要删除的文件路径

        @throws {FileNotFoundError} - 路径不是文件或文件不存在时抛出该异常
        @throws {PermissionError} - 没有权限时抛出该异常

        """
        if os.path.isfile(filename):
            os.remove(filename)
        else:
            raise FileNotFoundError

    @staticmethod
    def remove_sub_dirs(path='', regex_str=''):
        """
        删除指定目录下的子目录（及子目录下的文件和目录）

        @param {string} path='' - 需要删除的子目录的目录
        @param {string} regex_str='' - 需匹配目录名的正则表达式（''代表无需匹配）

        @throws {FileNotFoundError} - 当path不存在的情况下，会抛出该异常
        @throws {PermissionError} - 没有权限时抛出该异常
        @throws {NotADirectoryError} - 如果给出的路径不是目录而是文件时抛出

        """
        _dirs = FileTool.get_dirlist(path=path, regex_str=regex_str, is_fullpath=True)
        for _dir in _dirs:
            FileTool.remove_dir(_dir)

    @staticmethod
    def remove_files(path='', regex_str=''):
        """
        删除指定目录下的文件

        @param {string} path='' - 需要删除的文件的目录
        @param {string} regex_str='' - 需匹配文件名的正则表达式（''代表无需匹配）

        @throws {FileNotFoundError} - 当path不存在的情况下，会抛出该异常
        @throws {PermissionError} - 没有权限时抛出该异常
        @throws {NotADirectoryError} - 如果给出的路径不是目录而是文件时抛出

        """
        _files = FileTool.get_filelist(path=path, regex_str=regex_str, is_fullname=True)
        for _file in _files:
            FileTool.remove_file(_file)

    @staticmethod
    def remove_all_with_path(path='', regex_str=''):
        """
        删除指定文件夹下的所有文件及文件夹

        @param {string} path='' - 要处理的文件夹
        @param {string} regex_str='' - 文件名匹配的正则表达式

        """
        _pattern = None
        _path = os.path.realpath(path)
        _file_names = os.listdir(_path)
        if regex_str != "":
            _pattern = re.compile(regex_str)
        for fn in _file_names:
            if _pattern is not None:
                if not _pattern.match(fn):
                    # 获取下一个
                    continue

            _full_filename = os.path.join(_path, fn)
            if os.path.isfile(_full_filename):
                # 删除文件
                FileTool.remove_file(_full_filename)
            else:
                # 删除文件夹
                FileTool.remove_dir(_full_filename)

    @staticmethod
    def copy_all_with_path(src_path='', dest_path='', regex_str=''):
        """
        复制指定文件夹下的所有文件及文件夹到目标文件夹

        @param {string} src_path='' - 源文件夹
        @param {string} dest_path='' - 目标文件夹
        @param {string} regex_str='' - 文件名匹配的正则表达式

        """
        _pattern = None
        _dest_path = os.path.realpath(dest_path)
        _src_path = os.path.realpath(src_path)
        _file_names = os.listdir(_src_path)
        if regex_str != "":
            _pattern = re.compile(regex_str)
        for fn in _file_names:
            if _pattern is not None:
                if not _pattern.match(fn):
                    # 获取下一个
                    continue

            _full_filename = os.path.join(_src_path, fn)
            _full_destname = os.path.join(_dest_path, fn)
            if os.path.isfile(_full_filename):
                # 复制文件
                shutil.copyfile(_full_filename, _full_destname)
            else:
                # 复制文件夹
                shutil.copytree(_full_filename, _full_destname)


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
