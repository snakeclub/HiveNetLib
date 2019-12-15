#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
控制台基本命令框架
@module base_cmd
@file base_cmd.py
"""
import os
import sys
import threading
import traceback
import time
import subprocess
import warnings
from collections import Iterator
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetLib.generic import CResult
from HiveNetLib.simple_i18n import _, get_global_i18n  # 装载全局的i18n快捷函数
from HiveNetLib.base_tools.run_tool import RunTool
from HiveNetLib.simple_queue import MemoryQueue, Empty
from HiveNetLib.prompt_plus import PromptPlus
from HiveNetLib.base_tools.string_tool import StringTool
from HiveNetLib.simple_xml import SimpleXml


__MOUDLE__ = 'base_cmd'  # 模块名
__DESCRIPT__ = u'控制台基本命令框架'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2019.12.15'  # 发布日期


class CmdBaseFW(object):
    """
    命令处理类框架类
    """

    #############################
    # 构造函数
    #############################
    def __init__(self, **kwargs):
        """
        构造函数

        @param {kwargs} - 传入初始化参数字典（config.xml的init_para字典）
            参数中可以设置的特殊参数如下：
            is_async=False {bool}  - 是否异步模式，如果设置为True，将会通过新启动线程的方式执行命令函数
                命令函数可以通过全局全局打印队列'CMD_BASE_PRINT_QUEUE'将打印信息输出给主进程打印
            is_i18n=False {bool} - 是否对返回输出的信息进行国际化转换（如果需要父类进行国际化，则应设置为True）
            ignore_case=False {bool} - 匹配命令是否忽略大小写(视需要传入，默认不区分大小写)

        @throws {Exception} - 如果初始化异常会抛出异常
        """
        self._kwargs = kwargs  # 初始化传入字典
        self._console_global_para = RunTool.get_global_var('CONSOLE_GLOBAL_PARA')
        self._init(**kwargs)

    def cmd_dealfun(self, message='', cmd='', cmd_para=''):
        """
        命令处理函数

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）

        @return {iter} - 执行命令完成后要输到屏幕的内容，必须iter对象（yield返回）
            注：如果是on_abort和on_exit可以返回CResult的iter对象
            注2：如果直接return，信息将传递不到prompt的处理函数中，暂时未搞清楚原因
        """
        warnings.simplefilter('ignore', ResourceWarning)  # 指定屏蔽资源警告
        if 'is_async' in self._kwargs.keys() and self._kwargs['is_async']:
            # 异步模式，通过新启动线程方式执行函数
            self._queue = RunTool.get_global_var('CMD_BASE_PRINT_QUEUE')
            if self._queue is None:
                # 设置一个新的队列
                self._queue = MemoryQueue()

            # 启动命令执行线程
            self._thread_running = True
            _thread = threading.Thread(
                target=self._asyn_thread_fun,
                args=(message, cmd, cmd_para, self._kwargs),
                name='Thread-Cmd-DealFun'
            )
            _thread.setDaemon(True)
            _thread.start()

            # 遍历队列以及检查线程是否结束
            while self._thread_running or not self._queue.empty():
                # 从队列获取对象并返回外部打印
                try:
                    _item = self._queue.get(block=False)
                    if type(_item) == CResult:
                        yield _item.msg
                    else:
                        yield str(_item)
                except Empty:
                    time.sleep(0.01)

            # 处理完成，最终返回空
            yield ''
            return
        else:
            # 同步模式，直接执行函数处理
            _result = self._cmd_dealfun(message=message, cmd=cmd, cmd_para=cmd_para, **self._kwargs)
            if 'is_i18n' in self._kwargs.keys() and self._kwargs['is_async']:
                # 需要国际化处理
                if isinstance(_result, Iterator):
                    # 是迭代器
                    for _item in _result:
                        yield self._i18n_result_obj(_item)
                else:
                    yield self._i18n_result_obj(_result)
            else:
                # 不需要国际化处理，直接执行函数即可
                if isinstance(_result, Iterator):
                    for _item in _result:
                        yield _item
                else:
                    yield _result
            # 增加一个换行
            yield '\r\n'

    #############################
    # 内部处理函数
    #############################
    def _i18n_result_obj(self, result):
        """
        公共的处理返回结果国际化处理函数

        @param {string|CResult|iter} result - 可能是三种对象的其中一种
        """
        _type = type(result)
        if _type == CResult:
            # 错误对象
            result.msg = _(result.i18n_msg_id, result.i18n_msg_paras)
            return result
        elif _type == str:
            # 字符串
            return _(result)
        elif isinstance(result, Iterator):
            # 是迭代器
            for _result in result:
                # 回调自己进行处理
                yield self._i18n_result_obj(_result)
        else:
            # 字符串处理
            return _(result)

    def _asyn_thread_fun(self, message='', cmd='', cmd_para='', kwargs=dict()):
        try:
            _result = self._cmd_dealfun(message=message, cmd=cmd, cmd_para=cmd_para, **kwargs)
            _i18n_result = ''
            if 'is_i18n' in self._kwargs.keys() and self._kwargs['is_async']:
                _i18n_result = self._i18n_result_obj(_result)
            else:
                # 不需要国际化处理
                _i18n_result = _result

            # 判断返回值并区别处理
            if isinstance(_i18n_result, Iterator):
                # 是迭代器
                for _item in _i18n_result:
                    self._queue.put(_item)
            elif _i18n_result != '':
                self._queue.put(_i18n_result)
        except Exception as err:
            # 出现异常，将异常的打印信息放入显示队列
            _print_str = 'Call Excepiton: %s\r\n%s' % (
                str(err), traceback.format_exc()
            )
            self._queue.put(_print_str)
        finally:
            self._thread_running = False

    @classmethod
    def _cmd_para_to_dict(cls, cmd_para):
        """
        将参数转换为字典格式

        @param {string} cmd_para - 命令参数

        @return {dict} - 参数字典，获取规则说明如下:
            长短参数、名字参数: key为参数名（长短参数带-，名字参数带=）, value为参数值
            其他参数: key为'{para}序号', value为参数值, 序号从1开始
        """
        # 获取命令执行参数
        _cmd_list = PromptPlus.get_cmd_para_list(cmd_para)
        _dict = dict()
        _seq = 1
        for _item in _cmd_list:
            if _item[0] != '':
                _dict[_item[0]] = _item[1].strip("'")
            else:
                _dict['{para}%d' % _seq] = _item[1].strip("'")
                _seq += 1
        # 返回字典
        return _dict

    #############################
    # 需具体实现类覆盖实现的类
    #############################
    def _init(self, **kwargs):
        """
        实现类需要覆盖实现的初始化函数

        @param {kwargs} - 传入初始化参数字典（config.xml的init_para字典）

        @throws {exception-type} - 如果初始化异常应抛出异常
        """
        pass

    def _cmd_dealfun(self, message='', cmd='', cmd_para='', **kwargs):
        """
        实现类需要覆盖实现的命令处理函数

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）
        @param {kwargs} - 传入的主进程的初始化kwargs对象

        @return {string|iter_string} - 执行命令完成后要输到屏幕的内容，可以是iter对象（yield返回）
            注：如果是on_abort和on_exit可以返回CResult对象
        """
        pass


class CmdDefault(CmdBaseFW):
    """
    匹配不到命令时执行的处理函数类
    """
    #############################
    # 实际处理函数
    #############################

    def _cmd_dealfun(self, message='', cmd='', cmd_para='', **kwargs):
        """
        默认命令处理函数(未匹配到的命令)

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）
        @param {kwargs} - 传入的主进程的初始化kwargs对象

        @return {string|iter_string} - 执行命令完成后要输到屏幕的内容，可以是iter对象（yield返回）
            注：如果是on_abort和on_exit可以返回CResult对象
        """
        return _("'$1' is not support command!", cmd)


class CmdOnAbort(CmdBaseFW):
    """
    客户取消本次输入执行的函数类
    Ctrl + C : abort,取消本次输入
    """

    #############################
    # 实际处理函数
    #############################
    def _cmd_dealfun(self, message='', cmd='', cmd_para='', **kwargs):
        """
        Ctrl + C : abort,取消本次输入

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）
        @param {kwargs} - 传入的主进程的初始化kwargs对象

        @return {string|iter_string} - 执行命令完成后要输到屏幕的内容，可以是iter对象（yield返回）
            注：如果是on_abort和on_exit可以返回CResult对象
        """
        return ''


class CmdOnExit(CmdBaseFW):
    """
    客户关闭命令行执行的函数类
    Ctrl + D : exit,关闭命令行
    """

    #############################
    # 实际处理函数
    #############################
    def _cmd_dealfun(self, message='', cmd='', cmd_para='', **kwargs):
        """
        Ctrl + D : exit,关闭命令行

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）
        @param {kwargs} - 传入的主进程的初始化kwargs对象

        @return {string|iter_string} - 执行命令完成后要输到屏幕的内容，可以是iter对象（yield返回）
            注：如果是on_abort和on_exit可以返回CResult对象
        """
        _tip = _('You will shutdown $1 console, continue?(y/N)',
                 self._console_global_para['name'])
        _back = input(_tip)
        if _back.upper() == 'Y':
            # 退出
            return CResult(code='10101', msg='Exit $1 Console', i18n_msg_paras=(self._console_global_para['name'],))
        else:
            # 取消退出
            return CResult(code='00000', msg='Cancel Exit')


class CommonCmd(CmdBaseFW):
    """
    通用命令处理
    支持help、syscmd命令
    """
    #############################
    # 构造函数，在里面增加函数映射字典
    #############################

    def _init(self, **kwargs):
        """
        实现类需要覆盖实现的初始化函数

        @param {kwargs} - 传入初始化参数字典（config.xml的init_para字典）

        @throws {exception-type} - 如果初始化异常应抛出异常
        """
        self._CMD_DEALFUN_DICT = {
            'help': self._help_cmd_dealfun,
            'setlanguage': self._setlanguage_cmd_dealfun,
            'syscmd': self._syscmd_cmd_dealfun,
            'pwd': self._pwd_cmd_dealfun,
            'cd': self._cd_cmd_dealfun
        }
        self._console_global_para = RunTool.get_global_var('CONSOLE_GLOBAL_PARA')

    #############################
    # 实际处理函数
    #############################
    def _cmd_dealfun(self, message='', cmd='', cmd_para='', **kwargs):
        """
        通用处理函数，通过cmd区别调用实际的处理函数

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）
        @param {kwargs} - 传入的主进程的初始化kwargs对象

        @return {string|iter_string} - 执行命令完成后要输到屏幕的内容，可以是iter对象（yield返回）
            注：如果是on_abort和on_exit可以返回CResult对象
        """
        # 获取真实执行的函数
        _real_dealfun = None  # 真实调用的函数
        if 'ignore_case' in kwargs.keys() and kwargs['ignore_case']:
            # 区分大小写
            if cmd in self._CMD_DEALFUN_DICT.keys():
                _real_dealfun = self._CMD_DEALFUN_DICT[cmd]
        else:
            # 不区分大小写
            if cmd.lower() in self._CMD_DEALFUN_DICT.keys():
                _real_dealfun = self._CMD_DEALFUN_DICT[cmd.lower()]

        # 执行函数
        if _real_dealfun is not None:
            return _real_dealfun(message=message, cmd=cmd, cmd_para=cmd_para, **kwargs)
        else:
            return _("'$1' is not support command!", (cmd, ))

    #############################
    # 指令处理函数
    #############################
    def _help_cmd_dealfun(self, message='', cmd='', cmd_para='', **kwargs):
        """
        帮助命令处理函数

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）

        @return {string} - 执行命令完成后要输到屏幕的内容
        """
        # 命令相关参数
        _CMD_HELP_INFO = self._console_global_para['CMD_HELP_INFO']
        _lang = self._console_global_para['language']

        _cmd_list = PromptPlus.get_cmd_para_list(cmd_para)
        if len(_cmd_list) == 0:
            # 没有传入任何参数，生成命令提示参数并返回
            _cmd_list_tips = ''
            for _key in _CMD_HELP_INFO.keys():
                _cmd_title = ''
                if _lang in _CMD_HELP_INFO[_key].keys():
                    _cmd_title = _CMD_HELP_INFO[_key][_lang][0]
                elif 'en' in _CMD_HELP_INFO[_key].keys():
                    _cmd_title = _CMD_HELP_INFO[_key]['en'][0]
                else:
                    _cmd_title = _CMD_HELP_INFO[_key][list(_CMD_HELP_INFO[_key].keys())[0]][0]
                _cmd_list_tips = '%s%s%s\r\n' % (
                    _cmd_list_tips,
                    StringTool.fill_fix_string(_key, 15, ' ', left=False),
                    _cmd_title.replace(
                        '{{VERSION}}', self._console_global_para['version']
                    ).replace(
                        '{{NAME}}', self._console_global_para['name']
                    ).replace(
                        '{{SHELL_CMD_NAME}}', self._console_global_para['shell_cmd_name']
                    )
                )
            # 返回提示信息
            return _cmd_list_tips

        # 处理某个命令的具体帮助信息
        _para_value = ''
        for _item in _cmd_list:
            if _item[0] == '':
                _para_value = _item[1]
                break
            elif _item[0] == '-c' or _item[0] == '-cmd':
                _para_value = _item[1]
                break

        if _para_value in _CMD_HELP_INFO.keys():
            # 显示指定命令帮助
            _help_info = None
            if _lang in _CMD_HELP_INFO[_para_value].keys():
                _help_info = _CMD_HELP_INFO[_para_value][_lang]
            elif 'en' in _CMD_HELP_INFO[_para_value].keys():
                _help_info = _CMD_HELP_INFO[_para_value]['en']
            else:
                _help_info = _CMD_HELP_INFO[_para_value][list(
                    _CMD_HELP_INFO[_para_value].keys())[0]]

            return '\r\n'.join(_help_info).replace(
                '{{VERSION}}', self._console_global_para['version']
            ).replace(
                '{{NAME}}', self._console_global_para['name']
            ).replace(
                '{{SHELL_CMD_NAME}}', self._console_global_para['shell_cmd_name']
            )
        else:
            # 没有匹配到命令
            return _("help not support '$1' command\r\n", (_para_value, ))

    def _syscmd_cmd_dealfun(self, message='', cmd='', cmd_para='', **kwargs):
        """
        执行操作系统命令处理函数

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）

        @return {string} - 执行命令完成后要输到屏幕的内容
        """
        _shell_encoding = self._console_global_para['shell_encoding']
        _cmd_list = PromptPlus.get_cmd_para_list(cmd_para)
        _is_start_cmd = False
        _is_ni = False
        _is_bg = False
        _is_ns = False
        _real_cmd = ''

        for _item in _cmd_list:
            if not _is_start_cmd:
                # 还要判断是否参数
                if _item[0] in ['-ni', '-bg', '-ns']:
                    if _item[0] == '-ni':
                        _is_ni = True
                    elif _item[0] == '-bg':
                        _is_bg = True
                    else:
                        _is_ns = True

                    # 判断是否开始了命令
                    if _item[1] != '':
                        _real_cmd = _item[1]
                        _is_start_cmd = True

                    # 处理下一个对象
                    continue
                else:
                    # 开始是正式的命令
                    _is_start_cmd = True

            # 开始命令部分的处理
            _real_cmd += (' %s%s%s' % (
                _item[0],
                (' ' if _item[0] != '' and _item[0][0: 1] == '-' and _item[1] != '' else ''),
                _item[1]
            ))

        # 去掉前面的空格
        _real_cmd = _real_cmd.lstrip()

        # 执行进程
        yield '%s: %s\r\n\r\n' % (_('Execute system command'), _real_cmd)
        _sp = subprocess.Popen(
            _real_cmd, close_fds=_is_bg,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            shell=True
        )

        # 循环等待执行完成
        _exit_code = None
        try:
            while True:
                try:
                    # 打印内容
                    if not _is_ns:
                        yield _sp.stdout.readline().decode(_shell_encoding)
                    _exit_code = _sp.poll()
                    if _exit_code is not None:
                        # 结束，打印异常日志
                        if not _is_ns:
                            yield _sp.stdout.read().decode(_shell_encoding)
                            if _exit_code != 0:
                                yield _sp.stderr.read().decode(_shell_encoding)
                        break
                    # 释放一下CPU
                    time.sleep(0.01)
                except KeyboardInterrupt:
                    if _is_ni:
                        # 不允许取消
                        yield '\r\n' + _("ommand Executing, can't exit execute job!")
                    else:
                        raise KeyboardInterrupt
        except KeyboardInterrupt:
            # 遇到 Ctrl + C 退出
            if not _is_bg:
                # 结束任务
                _sp.terminate()
                _exit_code = _sp.poll()
                yield '\r\n' + _("Cancle Command execute, exit job!")
            else:
                yield '\r\n' + _("Command execute in bg, exit monitor!")

        # 最后返回
        if _exit_code is not None:
            yield '\r\n%s : %d' % (_("Command done, exit code"), _exit_code)

        yield '\r\n'

    def _pwd_cmd_dealfun(self, message='', cmd='', cmd_para='', **kwargs):
        """
        显示当前工作目录命令

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）

        @return {string} - 执行命令完成后要输到屏幕的内容
        """
        return _('Current work path is: $1', self._console_global_para['work_path'])

    def _cd_cmd_dealfun(self, message='', cmd='', cmd_para='', **kwargs):
        """
        切换当前工作目录命令

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）

        @return {string} - 执行命令完成后要输到屏幕的内容
        """
        _word_path = cmd_para.strip()
        os.chdir(_word_path)  # 改变工作目录，如果没有异常则认为成功
        self._console_global_para['work_path'] = os.getcwd()
        return _('Current work path is: $1', self._console_global_para['work_path'])

    def _setlanguage_cmd_dealfun(self, message='', cmd='', cmd_para='', **kwargs):
        """
        修改显示语言

        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）

        @return {string} - 执行命令完成后要输到屏幕的内容
        """
        _lang = cmd_para.strip()
        if _lang == '':
            return _('language must be not null')
        self._console_global_para['language'] = cmd_para.strip()
        _i18n_obj = get_global_i18n()
        if _i18n_obj is not None:
            _i18n_obj.lang = self._console_global_para['language']
        # 修改配置文件中的默认语言
        _config_xml = SimpleXml(
            self._console_global_para['config_file'],
            encoding=self._console_global_para['config_encoding']
        )
        _config_xml.set_value(
            '/console/language',
            self._console_global_para['language']
        )
        _config_xml.save()
        return _("Current language set to '$1'", self._console_global_para['language'])


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
