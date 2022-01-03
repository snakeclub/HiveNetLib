#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import os
import copy
import subprocess
import time
import traceback
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from HiveNetLib.base_tools.string_tool import StringTool
from HiveNetLib.base_tools.file_tool import FileTool
from HiveNetLib.base_tools.run_tool import RunTool
from HiveNetLib.prompt_plus import PromptPlus
from HiveNetLib.base_tools.import_tool import ImportTool
from HiveNetLib.simple_i18n import _, SimpleI18N, set_global_i18n, get_global_i18n
from HiveNetLib.simple_xml import SimpleXml
from HiveNetLib.simple_log import Logger


"""
控制台服务框架模块
@module server
@file server.py
"""

__MOUDLE__ = 'server'  # 模块名
__DESCRIPT__ = u'控制台服务框架模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2019.12.3'  # 发布日期


class ConsoleServer(object):
    """
    控制台服务框架
    使用方法如下(使用程序目录假设为'/myapp/'):
        1. 将'conf/config.xml'文件复制到自己应用启动程序目录下，路径为'/myapp/conf/config.xml'
        2. 如果需要支持多语言，在自己程序目录下建i18n目录(/myapp/i18n/)，然后可以建立'message_语言标识.json'文件
        3. 自己实现命令执行函数，继承HiveNetLib.simple_console.base_cmd.CmdBaseFW
        4. 将自己的函数命令配置至'/myapp/conf/config.xml'的'cmd_list'中（参考）;
        5. 修改config.xml的name、version等信息;
        6. 在启动文件中的__main__中调用ConsoleServer.console_main初始化控制台
    """
    #############################
    # 静态函数
    #############################
    @staticmethod
    def console_main(execute_file_path=None, default_config_file=None, console_self_config: dict = None, **kwargs):
        """
        启动命令行框架的主函数

        @param {string} execute_file_path=None - 外部调用该函数应将程序主目录传入，这样才能找到配置文件
        @param {string} default_config_file=None - 如果您希望用不同的配置文件路径作为默认路径，可传入该函数指定
        @param {dict} console_self_config=None - 命令行自定义配置信息，将添加到全局参数中
        """
        # 获取命令行参数，需要外部传入config、encoding参数
        # 例如 console.py config=/conf/config.xml encoding=utf-8 help=y shell_cmd=以命令行方式执行命令 shell_cmdfile=cmdfile.txt cmdfile_encoding=utf-8
        CONSOLE_GLOBAL_PARA = RunTool.get_global_var('CONSOLE_GLOBAL_PARA')
        if CONSOLE_GLOBAL_PARA is None:
            CONSOLE_GLOBAL_PARA = {}
            RunTool.set_global_var('CONSOLE_GLOBAL_PARA', CONSOLE_GLOBAL_PARA)

        # 自定义配置信息
        CONSOLE_GLOBAL_PARA['console_self_config'] = console_self_config

        # 程序主目录
        if execute_file_path is None:
            CONSOLE_GLOBAL_PARA['execute_file_path'] = os.path.realpath(
                FileTool.get_file_path(__file__))
        else:
            CONSOLE_GLOBAL_PARA['execute_file_path'] = execute_file_path

        # 工作目录，可以通过cd命令切换，通过pwd命令查看工作目录路径
        CONSOLE_GLOBAL_PARA['work_path'] = os.getcwd()

        _cmd_opts = RunTool.get_kv_opts()
        _default_config_file = default_config_file
        if _default_config_file is None:
            _default_config_file = os.path.join(
                CONSOLE_GLOBAL_PARA['execute_file_path'], 'conf/config.xml')

        _config = (
            _default_config_file
        ) if 'config' not in _cmd_opts.keys() else _cmd_opts['config']
        _encoding = 'utf-8' if 'encoding' not in _cmd_opts.keys() else _cmd_opts['encoding']
        CONSOLE_GLOBAL_PARA['config_encoding'] = _encoding
        CONSOLE_GLOBAL_PARA['config_file'] = _config

        # 获取配置文件信息
        _config_xml = SimpleXml(os.path.realpath(_config), encoding=_encoding)
        _config_dict = _config_xml.to_dict()

        # 启动控制台服务
        _server = ConsoleServer(_config_dict['console'])

        # 判断是否
        if 'help' in _cmd_opts.keys():
            # 执行帮助命令
            _lang = _config_dict['console']['language']
            _help_tips = StringTool.json_to_object(
                _config_dict['console']['shell_cmd_help']
            )
            _tips = ''
            # 如果找不到对应的语言，优先找英语，如果再找不到就找第一个
            if _lang in _help_tips.keys():
                _tips = _help_tips[_lang]
            elif 'en' in _help_tips.keys():
                _tips = _help_tips['en']
            else:
                _tips = _help_tips[_help_tips.keys()[0]]

            _print_str = '\r\n'.join(_tips).replace(
                '{{VERSION}}', _config_dict['console']['version']
            ).replace(
                '{{NAME}}', _config_dict['console']['name']
            ).replace(
                '{{SHELL_CMD_NAME}}', _config_dict['console']['shell_cmd_name']
            )

            # 打印
            print(_print_str)
        elif 'shell_cmd' in _cmd_opts.keys():
            # 命令行模式执行
            _cmd_list = None
            if _cmd_opts['shell_cmd'][0: 1] == '[' and _cmd_opts['shell_cmd'][-1:] == ']':
                # 是json数组格式
                _cmd_list = StringTool.json_to_object(_cmd_opts['shell_cmd'])
            else:
                _cmd_list = [_cmd_opts['shell_cmd']]
            # 逐个命令执行
            for _cmd in _cmd_list:
                _result = _server.call_cmd_directly(_cmd, shell_cmd=True)
                if not _result.is_success():
                    # 执行有错误，不继续执行
                    exit(1)

            # 正常完成
            exit(0)
        elif 'shell_cmdfile' in _cmd_opts.keys():
            _file_encoding = None
            if 'cmdfile_encoding' in _cmd_opts.keys() and _cmd_opts['cmdfile_encoding'] != '':
                _file_encoding = _cmd_opts['cmdfile_encoding']
            _cmd_text = FileTool.get_file_text(_cmd_opts['shell_cmdfile'], encoding=_file_encoding)
            _cmd_text = _cmd_text.replace('\r\n', '\n').replace('\r', '\n')
            _cmd_list = _cmd_text.split('\n')
            # 逐个命令执行
            for _cmd in _cmd_list:
                _result = _server.call_cmd_directly(_cmd, shell_cmd=True)
                if not _result.is_success():
                    # 执行有错误，不继续执行
                    exit(1)

            # 正常完成
            exit(0)
        else:
            _server.start_console()

    #############################
    # 内部变量
    #############################
    _import_object_dict = None  # 登记已经导入的对象字典
    _CMD_HELP_INFO = None
    _CMD_PARA = None
    _CMD_LIST = None

    #############################
    # 构造函数
    #############################

    def __init__(self, config_dict):
        """
        初始化构造函数

        @param {dict} server_config_dict - 服务器的初始化参数字典（console节点）
        """
        # 初始化参数
        self._config_dict = copy.deepcopy(config_dict)

        # 将部分公共参数放到全局变量
        self._console_global_para = RunTool.get_global_var('CONSOLE_GLOBAL_PARA')
        self._console_global_para['name'] = self._config_dict['name']
        self._console_global_para['version'] = self._config_dict['version']
        self._console_global_para['shell_cmd_name'] = self._config_dict['shell_cmd_name']
        self._console_global_para['language'] = self._config_dict['language']
        self._console_global_para['shell_encoding'] = self._config_dict['shell_encoding']  # 控制台编码
        self._console_global_para['exit_with_prompt'] = self._config_dict.get(
            'exit_with_prompt', 'y')  # 是否提示退出

        # i18n多语言加载
        _trans_file_path = None
        if self._config_dict['i18n'] == '':
            _trans_file_path = os.path.join(
                self._console_global_para['execute_file_path'], 'i18n/'
            )
        else:
            _trans_file_path = self._config_dict['i18n']

        _i18n_obj: SimpleI18N = get_global_i18n()
        if _i18n_obj is None:
            _i18n_obj = SimpleI18N(
                lang=self._config_dict['language'],
                trans_file_path=_trans_file_path,
                trans_file_prefix='message',
                auto_loads=True
            )
        else:
            # 装载默认的多国语言
            _i18n_obj.load_trans_from_dir(
                _trans_file_path, 'message', encoding='utf-8', append=True
            )
            _i18n_obj.lang = self._config_dict['language']

        # 再装载自身命令的国际语言文件
        _i18n_obj.load_trans_from_dir(
            os.path.join(os.path.realpath(FileTool.get_file_path(__file__)), 'i18n/'),
            'message', encoding='utf-8', append=True
        )
        set_global_i18n(_i18n_obj)

        # 装载默认执行函数
        _temp_dict = self._config_dict['default_dealfun']
        self._default_cmd_dealfun = self._import_and_init_class(
            _temp_dict['module_name'],
            _temp_dict['class_name'],
            _temp_dict['extend_path'],
            _temp_dict['init_para'],
            as_name='' if 'as_name' not in _temp_dict.keys() else _temp_dict['as_name']
        ).cmd_dealfun

        _temp_dict = self._config_dict['on_abort']
        self._on_abort = self._import_and_init_class(
            _temp_dict['module_name'],
            _temp_dict['class_name'],
            _temp_dict['extend_path'],
            _temp_dict['init_para'],
            as_name='' if 'as_name' not in _temp_dict.keys() else _temp_dict['as_name']
        ).cmd_dealfun

        _temp_dict = self._config_dict['on_exit']
        self._on_exit = self._import_and_init_class(
            _temp_dict['module_name'],
            _temp_dict['class_name'],
            _temp_dict['extend_path'],
            _temp_dict['init_para'],
            as_name='' if 'as_name' not in _temp_dict.keys() else _temp_dict['as_name']
        ).cmd_dealfun

        # 遍历参数装载
        self._is_fw_help_command = False
        self._init_cmd_paras()

        # 加入到CONSOLE_GLOBAL_PARA参数中
        self._console_global_para['CMD_PARA'] = self._CMD_PARA
        self._console_global_para['CMD_HELP_INFO'] = self._CMD_HELP_INFO
        self._console_global_para['CMD_LIST'] = self._CMD_LIST

        # 检查help命令是否框架自带的，如果是则增加提示帮助
        if self._is_fw_help_command:
            self._CMD_PARA['help']['word_para'] = self._CMD_LIST

        # 控制台启动时的提示语言
        self._CONSOLE_TIPS = StringTool.json_to_object(self._config_dict['start_tips'])

        # 日志对象
        _logger = None
        if 'logger' in self._config_dict.keys():
            _logger = Logger.create_logger_by_dict(
                self._config_dict['logger'])

        # 颜色调整
        _color_set = self._config_dict.get('color_set', None)
        if _color_set is not None:
            _input_color = _color_set.get('input', None)
            if _input_color is not None:
                _color_set[''] = _input_color

        # 初始化命令行工具对象
        self._prompt = PromptPlus(
            message=self._config_dict['message'],
            default='',  # 默认输入值
            cmd_para=self._CMD_PARA,  # 命令定义参数
            default_dealfun=self._default_cmd_dealfun,  # 默认处理函数
            on_abort=self._on_abort,  # Ctrl + C 取消本次输入执行函数
            on_exit=self._on_exit,  # Ctrl + D 关闭命令行执行函数
            logger=_logger,  # 日志
            color_set=_color_set,  # 命令行配色方案
        )

        # 最后才添加这个对象
        self._console_global_para['prompt_obj'] = self._prompt  # 将命令行工具对象放到可访问的参数中

        # 执行命令处理类的后初始化函数
        for _key in self._import_object_dict.keys():
            if hasattr(self._import_object_dict[_key], 'init_after_console_init'):
                self._import_object_dict[_key].init_after_console_init()

    #############################
    # 公共函数
    #############################
    def start_console(self):
        """
        启动控制台服务

        @returns {CResult} - 启动结果，result.code：'00000'-成功，'21401'-服务不属于停止状态，不能启动，其他-异常
        """
        _lang = self._console_global_para['language']
        _tips = ''
        # 如果找不到对应的语言，优先找英语，如果再找不到就找第一个
        if _lang in self._CONSOLE_TIPS.keys():
            _tips = self._CONSOLE_TIPS[_lang]
        elif 'en' in self._CONSOLE_TIPS.keys():
            _tips = self._CONSOLE_TIPS['en']
        else:
            _tips = self._CONSOLE_TIPS[self._CONSOLE_TIPS.keys()[0]]

        _tips_str = '\r\n'.join(_tips).replace(
            '{{VERSION}}', self._config_dict['version']
        ).replace(
            '{{NAME}}', self._config_dict['name']
        ).replace(
            '{{SHELL_CMD_NAME}}', self._config_dict['shell_cmd_name']
        )

        if self._auto_run_fun is not None:
            # 自动执行一个命令
            self._prompt.prompt_print(_('auto run: $1', '"%s.%s.cmd_dealfun(cmd=\'%s\', cmd_para=\'%s\')"' % (
                self._config_dict['auto_run']['module_name'],
                self._config_dict['auto_run']['class_name'],
                self._config_dict['auto_run']['run_cmd'],
                self._config_dict['auto_run']['run_cmd_para'],
            )))

            try:
                # 执行
                self._auto_run_fun(
                    message='',
                    cmd=self._config_dict['auto_run']['run_cmd'],
                    cmd_para=self._config_dict['auto_run']['run_cmd_para'],
                    prompt_obj=self._prompt
                )
            except:
                self._prompt.prompt_print(
                    '%s:\n%s' % (
                        _('auto run exception [$1]', str(sys.exc_info()[0])),
                        traceback.format_exc()
                    )
                )

        # 启动控制台服务
        self._prompt.start_prompt_service(
            tips=_tips_str,
            is_async=False,
            is_print_async_execute_info=True
        )

    def call_cmd_directly(self, cmd_str, shell_cmd: bool = False):
        """
        外部直接使用实例执行命令, 不通过命令行获取

        @param {string} cmd_str - 要实行的命令(含命令本身和参数)
        @param {bool} shell_cmd=False - 是否命令行直接执行模式
        """
        self._prompt.prompt_print(_('call cmd by shell mode: $1', cmd_str))
        return self._prompt.call_cmd_directly(cmd_str, shell_cmd=shell_cmd)

    #############################
    # 内部函数
    #############################
    def _import_and_init_class(self, module_name, class_name, extend_path, init_para, as_name=''):
        """
        装载并初始化对象返回（如果对象已存在则直接返回）

        @param {string} module_name - 模块名
        @param {string} class_name - 处理类名
        @param {string} extend_path - 模块所在搜索路径
        @param {string} init_para - 初始化的json字符串
        @param {string} as_name - 对象别名，可以设置不一样的值让类可以多次实例化

        @return {object} - 初始化后的模块对象

        @throws {ImportError} - 初始化失败返回该异常
        """
        # 检查对象是否已存在
        _key = as_name
        _class_tag = '%s.%s' % (module_name, class_name)
        if as_name == '':
            _key = _class_tag

        if self._import_object_dict is None:
            self._import_object_dict = dict()
        if _key in self._import_object_dict.keys():
            # 已存在，直接返回即可
            return self._import_object_dict[_key]

        # 装载模块
        _class = None
        if ImportTool.check_module_imported(module_name):
            # 模块已存在
            _class = ImportTool.get_member_from_module(
                ImportTool.get_imported_module(module_name),
                class_name
            )
        else:
            # 动态装载模块
            _class = ImportTool.get_member_from_module(
                ImportTool.import_module(
                    module_name,
                    extend_path=extend_path
                ),
                class_name
            )

        if _class is None:
            raise ImportError(_("config file error: can't import module: $1!", (_class_tag, )))

        # 初始化对象并返回
        _init_para = dict()
        if init_para != '':
            _init_para = StringTool.json_to_object(init_para)
        self._import_object_dict[_key] = _class(**_init_para)
        return self._import_object_dict[_key]

    def _init_cmd_paras(self):
        """
        初始化控制台参数
        实现self._CMD_HELP_INFO和self._CMD_PARA字典的装载
        """
        if self._CMD_LIST is None:
            self._CMD_LIST = dict()
        else:
            self._CMD_LIST.clear()

        if self._CMD_HELP_INFO is None:
            self._CMD_HELP_INFO = dict()
        else:
            self._CMD_HELP_INFO.clear()

        if self._CMD_PARA is None:
            self._CMD_PARA = dict()
        else:
            self._CMD_PARA.clear()

        self._auto_run_fun = None
        if 'auto_run' in self._config_dict.keys() and self._config_dict['auto_run']['class_name'] != '':
            # 装载执行函数
            self._auto_run_fun = self._import_and_init_class(
                self._config_dict['auto_run']['module_name'],
                self._config_dict['auto_run']['class_name'],
                self._config_dict['auto_run']['extend_path'],
                self._config_dict['auto_run']['init_para'],
                as_name='' if 'as_name' not in self._config_dict.keys(
                ) else self._config_dict['as_name']
            ).cmd_dealfun

        # 遍历cmd_list进行装载命令参数
        for _item in self._config_dict['cmd_list']:
            # 检查help命令是否自带命令
            if _item['command'] == 'help' and _item['module_name'] == 'HiveNetLib.simple_console.base_cmd':
                self._is_fw_help_command = True

            # 命令清单
            self._CMD_LIST[_item['command']] = None

            try:
                # 帮助信息
                self._CMD_HELP_INFO[_item['command']] = StringTool.json_to_object(_item['help'])
            except Exception as e:
                print('config file cmd [%s] help json string error!' % _item['command'])
                raise e

            try:
                # 命令信息
                self._CMD_PARA[_item['command']] = StringTool.json_to_object(_item['cmd_para'])
            except Exception as e:
                print('config file cmd [%s] cmd_para json string error!' % _item['command'])
                raise e

            # 处理函数
            self._CMD_PARA[_item['command']]['deal_fun'] = self._import_and_init_class(
                _item['module_name'],
                _item['class_name'],
                _item['extend_path'],
                _item['init_para'],
                as_name='' if 'as_name' not in _item.keys() else _item['as_name']
            ).cmd_dealfun


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
