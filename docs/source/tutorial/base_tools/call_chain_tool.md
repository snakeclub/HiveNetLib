# base_tools.call_chain_tool使用说明

call_chain_tool是用于产生调用链日志（包括接口调用、函数调用）的处理工具，原理是通过日志记录函数调用记录，并根据trace_id（追踪ID）、parent_call_id（父函数执行ID）等信息找到函数及接口之间的调用关系。通过修饰符方式来实现链的向下延伸，无需实际逻辑函数自身实现调用链相关代码。



## CallChainTool工具类

### 方法调用链标准应用

#### 第1步：定义日志类

使用调用链必须先定义日志类，用于将调用链日志信息输出到指定的日志载体中（具体记录在文件还是其他设备上由日志类控制），可以通过修饰符参数指定是使用通用的日志类，还是使用独立的日志类。

自行实现的日志类必须实现info、warning、error等标准写日志方法（参考Python自带的logging类）。

以下示例为使用simple_log日志类及使用全局通用日志类写日志：

```
from HiveNetLib.simple_log import Logger, EnumLoggerName, EnumLoggerConfigType

        # 初始化日志类
        _logger = Logger(
            conf_file_name=_TEMP_DIR + '/../../call_chain_tool/test_call_chain.json',
            logger_name=EnumLoggerName.ConsoleAndFile.value,
            logfile_path=_TEMP_DIR + '/log/test_case1.log',
            is_create_logfile_by_day=True,
            is_print_file_name=True,
            is_print_fun_name=True
        )
        # 设置为全局使用
        CallChainTool.set_global_logger(_logger)
```



#### 第2步：在需要追踪的函数定义上增加修饰符

注意：要追踪的调用函数必须都要加上调用链修饰符，比如a call b，b call c， c call d，则abcd都要加上调用链修饰符，如果c不增加修饰符，则无法从a 追踪到 d。

```
# 嵌套调用，产生调用链
@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=('k1'))
def func_case1_call_1(a, b, **kwargs):
    CallChainTool.get_global_logger().log(logging.INFO,
        'runing func_case1_call_1 : a=%s, b=%s : %s' % (str(a), str(b), str(kwargs)))
    time.sleep(0.001)
    # 执行2
    func_case1_call_2('2a', '2b', '2c', k1=kwargs['k1'])
    # 执行3
    func_case1_call_3(k1=kwargs['k1'])
    return


@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=('k1'))
def func_case1_call_2(a, b, c, **kwargs):
    CallChainTool.get_global_logger().log(logging.INFO,
        'runing func_case1_call_2 : a=%s, b=%s, c=%s: %s' % (str(a), str(b), str(c), str(kwargs)))
    time.sleep(0.001)
    # 执行4
    func_case1_call_4('4a', '4b', '4c', k1=kwargs['k1'])
    return


@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=('k1'))
def func_case1_call_3(**kwargs):
    CallChainTool.get_global_logger().log(logging.INFO,
        'runing func_case1_call_3 : %s' % (str(kwargs)))
    time.sleep(0.001)
    return


@CallChainTool.methon_call_chain(is_use_global_logger=True, key_para=('k1'))
def func_case1_call_4(a, b, c, **kwargs):
    CallChainTool.get_global_logger().log(logging.INFO,
        'runing func_case1_call_4 : a=%s, b=%s, c=%s: %s' % (str(a), str(b), str(c), str(kwargs)))
    time.sleep(0.001)
    return
```



#### 第3步：直接执行函数，将自动产生调用链日志

```
func_case1_call_1('1a', '1b', k1='testk1')
```

产生的日志符合HiveNet日志规范，TRACE : 调用关系追踪信息，里面登记多个信息，通过冒号（“:”）分隔，按顺序依次为TRACE_ID（追踪ID）、CALL_FILE（调用文件）、CALL_FUN（调用函数名）、TRACE_LEVEL（调用层级，每CALL一个下级函数+1）、PARENT_CALL_ID（父调用函数的执行ID）、CALL_ID（执行ID）

第1个函数（发起函数）的TRACE_ID自动生成；通过TRACE_ID可以找到本次执行调用的所有函数；通过PARENT_CALL_ID和CALL_ID可以依次向下找到调用关系；通过TRACE_LEVEL可以确定调用顺序。

示例如下：

```
[2018-09-11 23:16:14,595][INFO][PID:7716][TID:420][FILE:call_chain_tool.py][FUN:wrapper2][TRACE:9fa68424b5d511e891fdc2335e3520d4:9fa68424b5d511e891fdc2335e3520d4::1:call_chain_tool.py:func_case1_call_1]{'key': {'k': 'None', '1': 'None'}, 'para': {}}
[2018-09-11 23:16:14,595][INFO][PID:7716][TID:420][FILE:test_call_chain_tool.py][FUN:func_case1_call_1]runing func_case1_call_1 : a=1a, b=1b : {'k1': 'testk1', 'trace_id': '9fa68424b5d511e891fdc2335e3520d4', 'trace_level': [1], 'call_id': '9fa68424b5d511e891fdc2335e3520d4', 'parent_id': ''}
[2018-09-11 23:16:14,610][INFO][PID:7716][TID:420][FILE:call_chain_tool.py][FUN:wrapper2][TRACE:9fa68424b5d511e891fdc2335e3520d4:9fa8e67ab5d511e8bb9cc2335e3520d4:9fa68424b5d511e891fdc2335e3520d4:2:call_chain_tool.py:func_case1_call_2]{'key': {'k': 'None', '1': 'None'}, 'para': {}}
[2018-09-11 23:16:14,610][INFO][PID:7716][TID:420][FILE:test_call_chain_tool.py][FUN:func_case1_call_2]runing func_case1_call_2 : a=2a, b=2b, c=2c: {'k1': 'testk1', 'trace_id': '9fa68424b5d511e891fdc2335e3520d4', 'trace_level': [2], 'call_id': '9fa8e67ab5d511e8bb9cc2335e3520d4', 'parent_id': '9fa68424b5d511e891fdc2335e3520d4'}
[2018-09-11 23:16:14,626][INFO][PID:7716][TID:420][FILE:call_chain_tool.py][FUN:wrapper2][TRACE:9fa68424b5d511e891fdc2335e3520d4:9fab48ccb5d511e8acf9c2335e3520d4:9fa8e67ab5d511e8bb9cc2335e3520d4:3:call_chain_tool.py:func_case1_call_4]{'key': {'k': 'None', '1': 'None'}, 'para': {}}
[2018-09-11 23:16:14,626][INFO][PID:7716][TID:420][FILE:test_call_chain_tool.py][FUN:func_case1_call_4]runing func_case1_call_4 : a=4a, b=4b, c=4c: {'k1': 'testk1', 'trace_id': '9fa68424b5d511e891fdc2335e3520d4', 'trace_level': [3], 'call_id': '9fab48ccb5d511e8acf9c2335e3520d4', 'parent_id': '9fa8e67ab5d511e8bb9cc2335e3520d4'}
[2018-09-11 23:16:14,642][INFO][PID:7716][TID:420][FILE:call_chain_tool.py][FUN:wrapper2][TRACE:9fa68424b5d511e891fdc2335e3520d4:9fab48ccb5d511e8acf9c2335e3520d4:9fa8e67ab5d511e8bb9cc2335e3520d4:3:call_chain_tool.py:func_case1_call_4][USE:0.015624s]
[2018-09-11 23:16:14,642][INFO][PID:7716][TID:420][FILE:call_chain_tool.py][FUN:wrapper2][TRACE:9fa68424b5d511e891fdc2335e3520d4:9fa8e67ab5d511e8bb9cc2335e3520d4:9fa68424b5d511e891fdc2335e3520d4:2:call_chain_tool.py:func_case1_call_2][USE:0.031249s]
[2018-09-11 23:16:14,642][INFO][PID:7716][TID:420][FILE:call_chain_tool.py][FUN:wrapper2][TRACE:9fa68424b5d511e891fdc2335e3520d4:9fadab26b5d511e899c9c2335e3520d4:9fa68424b5d511e891fdc2335e3520d4:4:call_chain_tool.py:func_case1_call_3]{'key': {'k': 'None', '1': 'None'}, 'para': {}}
[2018-09-11 23:16:14,642][INFO][PID:7716][TID:420][FILE:test_call_chain_tool.py][FUN:func_case1_call_3]runing func_case1_call_3 : {'k1': 'testk1', 'trace_id': '9fa68424b5d511e891fdc2335e3520d4', 'trace_level': [4], 'call_id': '9fadab26b5d511e899c9c2335e3520d4', 'parent_id': '9fa68424b5d511e891fdc2335e3520d4'}
[2018-09-11 23:16:14,657][INFO][PID:7716][TID:420][FILE:call_chain_tool.py][FUN:wrapper2][TRACE:9fa68424b5d511e891fdc2335e3520d4:9fadab26b5d511e899c9c2335e3520d4:9fa68424b5d511e891fdc2335e3520d4:4:call_chain_tool.py:func_case1_call_3][USE:0.015633s]
[2018-09-11 23:16:14,657][INFO][PID:7716][TID:420][FILE:call_chain_tool.py][FUN:wrapper2][TRACE:9fa68424b5d511e891fdc2335e3520d4:9fa68424b5d511e891fdc2335e3520d4::1:call_chain_tool.py:func_case1_call_1][USE:0.062506s]
```



### 方法调用链高阶应用

#### 支持函数定义类型

@CallChainTool.methon_call_chain修饰符要求函数必须有\*\*kwargs的动态可变KV变量参数，用于传递4个关键的调用链参数trace_id、trace_level、call_id、parent_id。如果所定义的函数没有\*\*kwargs参数，虽然不会执行出错，但无法传递和跟踪整个调用链执行情况，只能记录当前函数的执行日志（包括执行使用时间）。

支持的函数定义类型参考如下：

- def func(\*args, \*\*kwargs)

- def func(para1,  para2,  **kwargs)

- def func(para1,  para2,  para3=v3,  **kwargs)
- def func(**kwargs)

注意如果是func(\*args, \*\*kwargs)的类型，可以通过设置修饰符参数is_standard_def=True来提升执行效率（无需动态执行函数）。

#### 如何自行传递调用链参数

如果存在需要自行定义调用链参数的情况，例如收到一笔网络报文后，处理函数作为调用链开始，但需要使用网络传过来的trace_id时可以通过以下操作实现自定义调用链参数：

方式1：在修饰符参数指定

通过修饰符参数  “trace_id=, trace_level=, call_id=, parent_id=”  可以直接指定相关参数并传入到执行函数中。

```
@CallChainTool.methon_call_chain(trace_id='xxx', trace_level=[0], call_id='xx', parent_id='xx')
def func(...):
	...
```

方式2：在函数的kwargs参数中传递

在调用函数时，在函数的kwargs参数中设置trace_id、trace_level、call_id、parent_id的值。

```
@CallChainTool.methon_call_chain()
def func(... ,trace_id='xxx', trace_level=[0], call_id='xx', parent_id='xx'):
	...
```

注：在调用链监控设计中，可能存在部分内部函数的执行不希望打印追踪日志，这时可以在有修饰符的函数的kwargs参数中获取trace_id、trace_level、call_id、parent_id的值， 用以上两种方式按规则传递给下一个追踪函数即可（中间过程不处理）。

#### 特殊参数说明

指定打印的日志级别：log_level=logging.INFO

指定打印关键参数信息：key_para=(‘para_name’, 0, ..)，参数为一个数组，如果值为字符串，代表打印这个名字的参数值（对应函数的kwargs参数），如果为数字，代表打印第几个位置的参数（对应函数的args参数）；注意如果只有一个参数，写法必须为(0,) ，以标注这个是数组

指定打印参数信息：print_in_para=(‘para_name’, 0, ..)，格式与key_para一致

在函数执行后，指定打印出参（例如参数中有引用类型的情况，可能值会被改变）：print_out_para=(‘para_name’, 0, ..)，格式与key_para一致

函数执行后，是否打印返回对象（调用对象的\_\_str\_\_方法）:is_print_back=True