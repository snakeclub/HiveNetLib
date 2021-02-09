#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
流水号生成模块
@module simple_id
@file simple_id.py
"""

import os
import sys
import uuid
from time import monotonic as timefun
import threading
from abc import ABC, abstractmethod  # 利用abc模块实现抽象类
# 根据当前文件路径将包路径纳入，在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from HiveNetLib.formula import StructFormulaKeywordPara, FormulaTool
from HiveNetLib.base_tools.string_tool import StringTool
from HiveNetLib.base_tools.run_tool import RunTool


__MOUDLE__ = 'simple_id'  # 模块名
__DESCRIPT__ = u'流水号生成模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2019.08.02'  # 发布日期


class IdSourceFW(ABC):
    """
    Id生成源框架类, 定义Id生成源的标准处理
    Id生成源负责管理以下内容:
        1. 当前Id信息的持久化
        2. 向提出申请的Id池分配Id序号段
        3. 保障分配出去的Id信息的唯一性
        4. 对Id信息进行处理
    """
    #############################
    # 内部变量
    #############################
    _max_id = 9999999999
    _is_circle = True
    _min_id = 1
    _initial_id = None
    _lock = None  # id操作锁对象
    _is_overflow = False  # 标记当前序号是否已超过最大值，只有is_circle为False才有效

    #############################
    # 属性
    #############################
    @property
    def max_id(self):
        """
        id最大值
        @property {int}
        """
        return self._max_id

    @property
    def min_id(self):
        """
        id最小值
        @property {int}
        """
        return self._min_id

    @property
    def is_circle(self):
        """
        当到达最大值后是否循环处理
        @property {bool}
        """
        return self._is_circle

    @property
    def current_id(self):
        """
        返回当前的id值
        @property {int}
        """
        with self._lock:
            return self._get_current_id()

    @property
    def is_overflow(self):
        """
        标识id是否已经超过最大值
        @property {bool}
        """
        with self._lock:
            return self._get_is_overflow()

    #############################
    # 公开函数
    #############################
    def __init__(self, max_id=9999999999, is_circle=True, min_id=1, initial_id=None, **kwargs):
        """
        构造函数, 初始化Id生成源对象

        @param {int} max_id=9999999999 - Id的最大值，如果为0则代表不限制
        @param {bool} is_circle=True - 当达到最大值时是否循环从最小值开始处理
        @param {int} min_id=1 - Id的最小值
        @param {int} initial_id=None - id初始值，如果送入则代表重置id当前序号
        @param {kwargs} - 由具体实现类自定义初始化对象所需的参数

        """
        # 检查项
        if type(max_id) != int or max_id < 0:
            # 入参错误
            raise AttributeError('param "max_id" must be int and >= 0')

        if type(min_id) != int or min_id <= 0 or min_id > max_id:
            # 入参错误
            raise AttributeError('param "min_id" must be int and between 0 and %d' % max_id)

        if initial_id is not None and (
            type(initial_id) != int or initial_id > max_id or initial_id < min_id
        ):
            # 入参错误
            raise AttributeError(
                'param "initial_id" must be int and between %d and %d' % (min_id, max_id))

        # 初始参数赋值
        self._max_id = max_id
        self._is_circle = is_circle
        self._min_id = min_id
        self._initial_id = initial_id
        self._lock = self._get_id_operate_lock(**kwargs)

        # 执行实现类的初始化函数
        self._init(**kwargs)

        # 初始化id, 设置当前id的值
        if initial_id is not None:
            with self._lock:
                self._set_current_id(initial_id, **kwargs)

    def allocate(self, size, **kwargs):
        """
        分配指定大小的id序号

        @param {int} size - 要分配的id数量
        @param {kwargs} - 由具体实现类自定义的参数

        @return {tuple} - 返回的id序号范围(最小值, 最大值)
            注意：当需要获取的序号范围超过序号限制最大值时，返回的序号范围有可能小于size(只取到最大值)

        @throw {AttributeError} - size参数错误时抛出
        @throw {OverflowError} - id序号已经超过最大值时抛出
        """
        if type(size) != int or size <= 0:
            # 入参错误
            raise AttributeError('param "size" must be int and greater than 0')

        with self._lock:
            if self._get_is_overflow(**kwargs):
                # 已经超过最大值
                raise OverflowError('current id is overflow, max %s' % (str(self._max_id)))

            # 获取范围
            _min_id = self._get_current_id(**kwargs)
            _max_id = min(_min_id + size - 1, self._max_id)
            _current_id = _max_id + 1

            # 处理当前id
            if _current_id > self._max_id:
                # 当前id已经超过限制
                if self._is_circle:
                    # 循环情况，重置为最小值
                    _current_id = self._min_id
                else:
                    # 不支持循环，置为超限
                    self._set_is_overflow(True, **kwargs)

            # 更新并返回
            self._set_current_id(_current_id, **kwargs)
            return (_min_id, _max_id)

    def set_current_id(self, id, **kwargs):
        """
        设置当前id序号

        @param {int} id - 要设置的id
        @param {kwargs} - 由具体实现类自定义的参数
        """
        if id > self._max_id or id < self._min_id:
            raise AttributeError('id must between %d and %d' % (self._min_id, self._max_id))

        with self._lock:
            self._set_current_id(id, **kwargs)
            if self._get_is_overflow(**kwargs):
                self._set_is_overflow(False, **kwargs)

    #############################
    # 可以按需要重载的函数
    #############################
    def _get_id_operate_lock(self, **kwargs):
        """
        获取id操作锁对象
        函数默认取threading.RLock作为锁对象, 可根据需求更换其他操作锁

        @param {kwargs} - 由具体实现类自定义的参数，传入的是__init__函数的自定义值

        @return {object} - 返回锁实例对象，要求对象必须支持with，即包含两个内置函数:
            __enter__ : with进入，获取id操作锁
            __exit__ : with结束，释放id操作锁
        """
        return threading.RLock()

    def _set_is_overflow(self, is_owerflow, **kwargs):
        """
        设置is_owerflow的值
        函数默认设置当前对象的_is_owerflow属性，可以根据需求自定义（例如放远程服务器上的变量）

        @param {bool} is_owerflow - 要设置的is_owerflow的值
        @param {kwargs} - 由具体实现类自定义的参数
        """
        self._is_overflow = is_owerflow

    def _get_is_overflow(self, **kwargs):
        """
        获取is_owerflow的值
        函数默认获取当前对象的_is_owerflow属性，可以根据需求自定义（例如放远程服务器上的变量）

        @param {kwargs} - 由具体实现类自定义的参数
        """
        return self._is_overflow

    #############################
    # 需重载的函数
    #############################
    @abstractmethod
    def _init(self, **kwargs):
        """
        自定义的构造函数

        @param {kwargs} - 由具体实现类自定义的参数

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常
        """
        raise NotImplementedError

    @abstractmethod
    def _set_current_id(self, id, **kwargs):
        """
        设置当前id的值

        @param {int} id - 要设置的id值
        @param {kwargs} - 由具体实现类自定义的参数
            注：如果初始化对象的时候，会将构造函数的kwargs传入, 需在定义的时候注意

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常
        """
        raise NotImplementedError

    @abstractmethod
    def _get_current_id(self, **kwargs):
        """
        获取当前id的值

        @return {int} - 返回当前id的值

        @throws {NotImplementedError} - 当实现类没有实现该方法时，抛出该异常
        """
        raise NotImplementedError


class IdSourceMemory(IdSourceFW):
    """
    内存Id生成源
    注意: Id仅程序运行期间有效，无持久化，不支持跨进程
    """
    #############################
    # 内部变量
    #############################
    _id = 1  # 存储当前id值的变量

    #############################
    # 需重载的函数
    #############################
    def _init(self, **kwargs):
        """
        自定义的构造函数

        @param {kwargs} - 由具体实现类自定义的参数（无参数定义）

        """
        # 将当前id赋值为最小值
        self._set_current_id(self._min_id, **kwargs)

    def _set_current_id(self, id, **kwargs):
        """
        设置当前id的值

        @param {int} id - 要设置的id值
        @param {kwargs} - 由具体实现类自定义的参数
        """
        self._id = id

    def _get_current_id(self, **kwargs):
        """
        获取当前id的值

        @return {int} - 返回当前id的值
        """
        return self._id


class IdPool(object):
    """
    Id资源池
    1、负责从Id生成源获取Id序号段，形成资源池
    2、提供应用获取Id的方法
    3、按指定规则生成特定格式的流水号
    """
    #############################
    # 静态函数
    #############################
    @staticmethod
    def default_formula_deal_fun_id(formular_obj, **kwargs):
        """
        默认公式计算函数-格式化id（左补0）

        @param {StructFormula} formular_obj - 要计算的公式
        @param {kwargs} - 处理公式的参数，必须传进来的参数为
            id {int} - 要格式化的id

        """
        if formular_obj.content_string == '':
            formular_obj.formula_value = str(kwargs['id'])
        else:
            formular_obj.formula_value = StringTool.fill_fix_string(
                str(kwargs['id']),
                fix_len=int(formular_obj.content_string),
                fill_char='0'
            )

    #############################
    # 内部变量
    #############################
    _id_source = None
    _alloc_size = 50
    _alloc_lower_size = 10
    _is_deamon = False
    _is_use_formula = False
    _formula_str = ''
    _formula_tool = None
    # 内部控制函数
    _id_operate_lock = None  # id处理的控制锁对象
    _is_overflow = False  # 标记当前序号是否已无法获取到
    # 资源池列表，申请资源时将[min_id, max_id]添加到列表末尾
    # 取出id时优先从第一个对象的序号段中获取，取完就删除第一个序号段
    # 注意应在__init__中初始化，否则会出现两个实例对象引用地址一样的问题
    _id_pool = None
    _pool_size = 0  # 当前资源池的大小
    _allocate_thread_stop_tag = False  # 控制申请线程是否结束
    _allocate_thread_running = False  # 标注申请线程是否正在执行
    _allocate_thread_status_lock = None  # 更新线程状态的锁

    #############################
    # 公共属性
    #############################
    @property
    def pool_size(self):
        """
        返回当前资源池大小
        @property {int}
        """
        return self._pool_size

    @property
    def is_overflow(self):
        """
        标记当前资源池序号是否已无法获取到
        @property {bool}
        """
        return self._is_overflow

    #############################
    # 公共函数
    #############################
    def __init__(self, id_source, alloc_size=50, alloc_lower_size=10, is_deamon=False,
                 is_use_formula=False, formula_str='{$ID=$}', formula_tool=None, **kwargs):
        """
        构造函数

        @param {IdSourceFW} id_source - Id生成源对象
        @param {int} alloc_size=50 - 每次申请Id段的大小
        @param {int} alloc_lower_size=10 - 当Id池数少于多少时重新申请
        @param {bool} is_deamon=False - 是否通过守护程序申请Id段
            True - 启动一个单独守护线程检查Id池的数量，不足时自动获取新的Id段
            False - 在应用获取Id时检查Id池的数量，不足时自动启动新线程获取新的Id段
        @param {bool} is_use_formula=False - 是否使用公式处理id
            True - 使用公式返回格式化后的id字符串
            False - 直接返回原始id
        @param {string} formula_str='[id]' - 默认的id格式化公式(get_id不传公式的情况下使用)
        @param {HiveNetLib.formula.FormulaTool} formula_tool=None - 公式处理对象
            可以自定义公式处理对象，如果不传，则默认创建一个标准公式对象，可支持的公式格式说明如下：
            {$PY=要执行的公式$}、{$ID=左补0的长度（空代表不补）$}、{$TIME=时间格式字符串$}
        """
        self._id_source = id_source
        self._alloc_size = alloc_size
        self._alloc_lower_size = alloc_lower_size
        self._is_deamon = is_deamon
        self._id_operate_lock = self._get_id_operate_lock(**kwargs)
        self._id_pool = list()
        self._allocate_thread_status_lock = threading.RLock()

        # 处理公式类
        self._is_use_formula = is_use_formula
        self._formula_str = formula_str
        self._formula_tool = formula_tool
        if is_use_formula and formula_tool is None:
            # 初始化标准公式类
            # 定义字符串公式的公共关键字参数，例如python中的""引起来的认为是字符串
            _string_para = StructFormulaKeywordPara()
            _string_para.is_string = True  # 声明是字符串参数
            _string_para.has_sub_formula = False  # 声明公式中不会有子公式
            # 在查找字符串结束关键字时忽略的转义情况，例如"this is a string ,ignore \" , this is real end"
            _string_para.string_ignore_chars = ['\\"', '""']

            # 定义公式解析的关键字参数
            _keywords = {
                # 字符串的公式匹配参数, 以双引号开头, 双引号结束，字符串内部不会有嵌套公式
                'String': [
                    ['"', list(), list()],  # 公式开始标签
                    ['"', list(), list()],  # 公式结束标签
                    _string_para  # 公式检索参数
                ],
                # Python语言公式，自动计算内容，例如{$PY=100+50*3$}
                'PY': [
                    ['{$PY=', list(), list()],  # 公式开始标签
                    ['$}', list(), list()],  # 公式结束标签
                    StructFormulaKeywordPara()  # 公式检索参数
                ],
                # 指示放入ID信息，值为ID的长度，如果值不为空代表左补零，例如{$ID=10$}
                'ID': [
                    ['{$ID=', list(), list()],
                    ['$}', list(), list()],
                    StructFormulaKeywordPara()
                ],
                # 指示放入时间日期，值为时间日期的格式，例如{$TIME=%Y%m%d%H%M%S$}
                'TIME': [
                    ['{$TIME=', list(), list()],
                    ['$}', list(), list()],
                    StructFormulaKeywordPara()
                ]
            }

            # 定义公式对象处理函数
            _deal_fun_list = {
                'String': FormulaTool.default_deal_fun_string_content,  # 只保留标签内容
                'PY': FormulaTool.default_deal_fun_python,  # 执行python语句
                'TIME': FormulaTool.default_deal_fun_datetime_str,  # 获取日志格式
                'ID': IdPool.default_formula_deal_fun_id  # 获取ID
            }

            # 初始化公式类
            self._formula_tool = FormulaTool(
                keywords=_keywords,
                ignore_case=False,
                deal_fun_list=_deal_fun_list,
                default_deal_fun=None
            )

        # 执行自定义的初始化函数
        self._init(**kwargs)
        # 启动线程
        if self._is_deamon:
            self._start_allocate_thread()

    def get_id(self, overtime=0, **kwargs):
        """
        获取一个id

        @param {number} overtime=0 - 超时时间，单位为秒，如果需要一直不超时送入0
        @param {kwargs} - 由具体实现类自定义的参数，其中本实现类的可选参数如下：
            formula_str {string} - id格式化公式，当资源池的is_use_formula为True时有效，如果调用函数
                时传入该参数，则以该参数对应的公式进行id的格式化处理；如果不传入参数，则以构造函数的默
                认格式化公式进行格式化处理

        @return {int|string} - 返回id序号或格式化后的Id字符串，具体什么格式由id资源池创建参数确定
        """
        _current_id = self._get_original_id(overtime=overtime, **kwargs)
        if self._is_use_formula:
            # 按公式返回
            _formula_str = ''
            if 'formula_str' in kwargs.keys():
                _formula_str = kwargs['formula_str']
            else:
                _formula_str = self._formula_str
            # 返回格式化的内容
            return self._formula_tool.run_formula_as_string(_formula_str, id=_current_id).formula_value
        else:
            # 直接返回id
            return _current_id

    #############################
    # 内部函数
    #############################
    def __del__(self):
        """
        析构函数，结束线程
        """
        with self._allocate_thread_status_lock:
            self._allocate_thread_stop_tag = True

    def _allocate(self, **kwargs):
        """
        申请一个Id段并添加资源池中
        """
        try:
            _min_id, _max_id = self._id_source.allocate(self._alloc_size, **kwargs)
            # print('_allocate: %d, %d' % (_min_id, _max_id))
            # 添加到资源池中
            with self._id_operate_lock:
                self._id_pool.append([_min_id, _max_id])
                self._pool_size += (_max_id - _min_id + 1)
                self._is_overflow = False
        except OverflowError:
            # 已经超过了id最大限制,更新标记并返回就好
            self._is_overflow = True

    def _get_original_id(self, overtime=0, **kwargs):
        """
        获取一个原始id值

        @param {number} overtime=0 - 超时时间，单位为秒，如果需要一直不超时送入0

        @throw {OverflowError} - 当无法再申请到id号段且池子里也没有id的情况下抛出该异常
        @throw {TimeoutError} - 尝试获取id超时
        """
        endtime = timefun() + overtime
        while True:
            # 尝试获取资源
            _current_id = None
            with self._id_operate_lock:
                if self._pool_size > 0:
                    # 有Id资源，获取一个并返回
                    self._pool_size -= 1
                    _current_id = self._id_pool[0][0]
                    if _current_id == self._id_pool[0][1]:
                        # 当前号段已经用完了，移除号段
                        self._id_pool.pop(0)
                    else:
                        # 号段减少
                        self._id_pool[0][0] = _current_id + 1

            # 判断是否已经溢出无法获取id
            if self._is_overflow and _current_id is None:
                raise OverflowError('current id is overflow')

            # 自动发起号段申请
            if not self._is_deamon and self._pool_size < self._alloc_lower_size:
                self._start_allocate_thread()

            # 返回结果或判断是否超时
            if _current_id is None:
                if overtime > 0:
                    remaining = endtime - timefun()
                    if remaining <= 0.0:
                        raise TimeoutError('get original id timeout')
                # 没有超时，循环
                RunTool.sleep(0.01)
                continue
            else:
                return _current_id

    def _start_allocate_thread(self):
        """
        启动号段申请线程，内部区分是否守护线程模式
        """
        with self._allocate_thread_status_lock:
            if self._allocate_thread_running:
                # 线程已经启动了，无需再处理
                return
            else:
                # 标识线程被启动
                self._allocate_thread_running = True

        if self._is_deamon:
            # 守护线程模式，等删除对象时才结束线程
            self._allocate_thread_stop_tag = False
        else:
            # 非守护线程模式，只执行一次
            self._allocate_thread_stop_tag = True

        # 启动线程
        _allocate_thread = threading.Thread(
            target=self._allocate_thread_fun,
            args=(1,),
            name='Thread-IdPool-Alloc'
        )
        _allocate_thread.setDaemon(True)
        _allocate_thread.start()

    def _allocate_thread_fun(self, tid):
        """
        申请id号段线程

        @param {int} tid - 线程id
        """
        while True:
            # 申请Id段
            try:
                if self._pool_size < self._alloc_lower_size:
                    self._allocate()
            except:
                # 遇到异常不进行处理
                pass

            # 判断是否要退出
            if self._allocate_thread_stop_tag:
                break
            else:
                RunTool.sleep(0.1)

        # 线程结束，更新状态
        with self._allocate_thread_status_lock:
            self._allocate_thread_running = False

    #############################
    # 建议继承类自定义的处理函数
    #############################
    def _init(self, **kwargs):
        """
        自定义的构造函数

        @param {kwargs} - 由具体实现类自定义的参数
        """
        pass

    def _get_id_operate_lock(self, **kwargs):
        """
        获取id操作锁对象
        函数默认取threading.RLock作为锁对象, 可根据需求更换其他操作锁

        @param {kwargs} - 由具体实现类自定义的参数，传入的是__init__函数的自定义值

        @return {object} - 返回锁实例对象，要求对象必须支持with，即包含两个内置函数:
            __enter__ : with进入，获取id操作锁
            __exit__ : with结束，释放id操作锁
        """
        return threading.RLock()


class IdPoolUuid(object):
    """
    通过uuid产生唯一的ID，兼容IdPool的公共方法
    """
    #############################
    # 公共属性
    #############################
    @property
    def pool_size(self):
        """
        返回当前资源池大小, 永远返回9999
        @property {int}
        """
        return 9999

    @property
    def is_overflow(self):
        """
        标记当前资源池序号是否已无法获取到, 永远返回Fasle
        @property {bool}
        """
        return False

    #############################
    # 公共函数
    #############################
    def __int__(self, level=1, namespace=uuid.NAMESPACE_URL, name='uuid_name', is_clear_dash=False, **kwargs):
        """
        构造函数

        @param {int} level=1 - uuid的级别
            1 - uuid1, 基于MAC地址，时间戳，随机数来生成唯一的uuid，可以保证全球范围内的唯一性
            3 - uuid3, 通过计算一个命名空间和名字的md5散列值来给出一个uuid，所以可以保证命名空
                间中的不同名字具有不同的uuid，但是相同的名字就是相同的uuid了
            4 - uuid4, 通过伪随机数得到uuid，是有一定概率重复的
            5 - uuid5, 和uuid3基本相同，只不过采用的散列算法是sha1
        @param {uuid} namespace=uuid.NAMESPACE_URL - 命名空间，仅uuid3和uuid5使用，其实也是一个uuid,
            可选值包括：
                uuid.NAMESPACE_URL
                uuid.NAMESPACE_DNS
                uuid.NAMESPACE_OID
                uuid.NAMESPACE_X500
        @param {string} name='uuid_name' - 命名，仅uuid3和uuid5使用
        @param {bool} is_clear_dash=False - 是否清除破折号
        """
        self._level = level
        self._namespace = namespace
        self._name = name
        self._is_clear_dash = is_clear_dash
        # 定义uuid的函数
        if level == 3:
            self._uuidfun = uuid.uuid3
        elif level == 4:
            self._uuidfun = uuid.uuid4
        elif level == 5:
            self._uuidfun = uuid.uuid5
        else:
            self._uuidfun = uuid.uuid1

    def get_id(self, overtime=0, **kwargs):
        """
        获取一个id

        @param {number} overtime=0 - 超时时间，单位为秒，如果需要一直不超时送入0

        @return {string} - 返回id序号或格式化后的Id字符串，具体什么格式由id资源池创建参数确定
        """
        if self._level in [3, 5]:
            _namespace = self._namespace
            if 'namespace' in kwargs.keys():
                _namespace = kwargs['namespace']
            _name = self._name
            if 'name' in kwargs.keys():
                _name = kwargs['name']
            _id = self._uuidfun(_namespace, _name)
        else:
            _id = self._uuidfun()
        _id = str(_id)
        if self._is_clear_dash:
            _id = _id.replace('-', '')
        return _id


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
