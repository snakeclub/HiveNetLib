#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright 2018 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
网络处理相关工具

@module net_tool
@file net_tool.py

"""
import netifaces

__MOUDLE__ = 'net_tool'  # 模块名
__DESCRIPT__ = u'网络处理相关工具'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2018.08.29'  # 发布日期


class NetTool(object):
    """
    网络处理相关工具
    提供网络处理相关的函数，包括字节转换处理等

    """

    @staticmethod
    def int_to_bytes(int_value, fix_len=4, byte_order="big", signed=True):
        """
        将整型数据转换为字节数组,与bytes_to_int配套使用

        @param {int} int_value - 要转换的数字
        @param {int} fix_len=4 - 返回数组的长度，如果整数转换出的字节数组长度超过了该长度，则产生OverflowError
        @param {string} byte_order="big" - 字节顺序，值为'big'或者'little':
            big - 表示最有意义的字节放在字节数组的开头
            little - 表示最有意义的字节放在字节数组的结尾
            sys.byteorder - 保存了主机系统的字节序，可以使用这个属性获取本机顺序
        @param {bool} signed=True - 确定是否使用补码来表示整数，如果值为False，并且是负数，则产生OverflowError

        @returns {bytes} - 转换后的字节数组

        @throws {OverflowError} - 如果整数转换出的字节数组长度超过长度或无符号位时传入负数

        """
        return int_value.to_bytes(length=fix_len, byteorder=byte_order, signed=signed)

    @staticmethod
    def bytes_to_int(bytes_value, byte_order="big", signed=True):
        """
        将字节数组转换为整型数字，与int_to_bytes配套使用

        @param {bytes} bytes_value - 要转换的字节数组
        @param {string} byte_order="big" - 字节顺序，值为'big'或者'little':
            big - 表示最有意义的字节放在字节数组的开头
            little - 表示最有意义的字节放在字节数组的结尾
            sys.byteorder - 保存了主机系统的字节序，可以使用这个属性获取本机顺序
        @param {bool} signed=True - 确定是否使用补码来表示整数，如果值为False，并且是负数，则产生OverflowError

        @returns {int} - 转换后的整数

        @throws {OverflowError} - 无符号位时传入负数抛出该异常

        """
        return int.from_bytes(bytes_value, byteorder=byte_order, signed=signed)

    #############################
    # 获取网卡相关信息
    #############################
    @staticmethod
    def get_net_interfaces():
        """
        获取本机网卡清单

        @return {list} - 返回网卡名(NIC NAME)清单
            例如：['lo0', 'gif0', 'stf0', 'en0', 'en1', 'fw0']
        """
        return netifaces.interfaces()

    @staticmethod
    def get_net_interface_info(nic_name):
        """
        获取指定网卡的地址信息

        @param {string} nic_name - 网卡名(NIC NAME)

        @return {dict} - 返回网卡的地址信息，对应信息的Key为协议(部分研究出来的)：
            netifaces.AF_LINK -1000 物理地址 : {'addr' : 物理地址(MAC地址)}
            netifaces.AF_INET 2 互联网网络地址(ipv4) : {'addr': IP地址, 'netmask': 网络掩码, 'broadcast': 广播地址}
            netifaces.AF_INET6 23 互联网网络地址(ipv6): 跟AF_INET一样
            AF_12844 25
            AF_APPLETALK 16
            AF_ATM 22
            AF_BAN 21
            AF_CCITT 10
            AF_CHAOS 5
            AF_CLUSTER 24
            AF_DATAKIT 9
            AF_DECnet 12
            AF_DLI 13
            AF_ECMA 8
            AF_FIREFOX 19
            AF_HYLINK 15
            AF_IMPLINK 3
            AF_IPX 6
            AF_IRDA 26
            AF_ISO 7
            AF_LAT 14
            AF_NETBIOS 17
            AF_NETDES 28
            AF_NS 6
            AF_PUP 4
            AF_SNA 11
            AF_UNIX 1
            AF_UNKNOWN1 20
            AF_UNSPEC 0
            AF_VOICEVIEW 18
        """
        return netifaces.ifaddresses(nic_name)

    @staticmethod
    def get_net_gateways():
        """
        返回本机的网关信息清单

        @return {dict} - 网关信息清单，key为协议（见address_families, 除default不同），
            value为数组['地址', '使用该网关地址的网卡名NIC NAME', 是否默认网关]
            字典里有一个特殊key为'default'，可通过这个获取到默认网关信息
        """
        return netifaces.gateways()


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名：%s  -  %s\n'
           '作者：%s\n'
           '发布日期：%s\n'
           '版本：%s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
