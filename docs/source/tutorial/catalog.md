# HiveNetLib tutorial

HiveNetLib 是一个方便开发人员调用的，集合一些常用开发功能的开发Python库，包括网络编程（tcpip、http）、日志、命令行交互、公式计算等。

HiveNetLib 的目的是让开发人员用最简单的方法实现最常用的功能，提高开发效率，关注具体功能逻辑而非具体技术实现。

同时该库为开源项目HiveNet依赖的基础库。

## 安装方法

### 源码方式安装

- HiveNetLib库安装

1、下载整体源码到需要安装的服务器上；

2、通过命令行进入源码目录

3、执行编译命令：python setup.py build

4、执行安装命令：python setup.py install

PIPY安装：pip install HiveNetLib

注意：pip安装时可以通过 '--no-deps' 参数指定不安装依赖包，这样可以只针对所需使用的模块安装所需的依赖包（模块装载时会自动判断并安装）; 同时也可以执行通过 deps_tool.py 文件进行安装依赖包，具体安装方法通过以下命令查看 'python deps_tool.py'

- 安装包打包（2种方式）

1、python安装包方式：python setup.py sdist

安装：python setup.py install

2、python setup.py bdist_wheel

安装：pip install HiveNetLib-0.6.0-py3-none-any.whl

- 文档生成

1、命令行进入：HiveNetLib\docs

2、执行命令生成html文档：make html

文档生成依赖Sphinx，需安装以下包：

pip install -U Sphinx
pip install sphinx_rtd_theme
pip install recommonmark

此外需要支持SnakerPy格式（JSDoc风格）的注释，可以到 https://github.com/snakeclub/sphinx-ext-napoleon-snakerpy 下载napoleon扩展，增加对SnakerPy注释风格支持（安装方法参考sphinx-ext-napoleon-snakerpy 的文档）



## 库模块大纲

### 基础模块

#### generic

[generic](generic.md)模块主要实现一些公共的基础通用类，包括关键的NullObj（空对象定义类）和CResult(通用错误类)。



#### base_tools

实现一系列基础的基本工具，包括：

- value_tool :   值处理通用工具模块，提供从字典对象取值的方法实现，后续会按需持续扩展
- string_tool : 字符串处理模块, 提供字符串/字节/json/xml/dict/object相互转换、产生固定长度字符、字符查找等方法实现
- run_tool : 运行参数处理通用工具模块，提供全局变量处理、命令行入参、单进程运行控制、函数对象相关信息获取等方法实现
- net_tool : 网络处理相关工具模块，提供int/网络字节相互转换的方法实现，后续会按需持续扩展
- import_tool : 库导入工具模块，提供动态导入库及模块的方法实现
- file_tool : 文件处理工具模块, 提供文件及目录、zip压缩文件的相关方法实现
- test_tool : 测试相关工具模块，提供测试所需的对象比较相关方法实现，后续会按需持续扩展
- debug_tool : 通用调试工具模块，提供调式所需的打印相关方法
- [exception_tool](base_tools/exception_tool.md) : 异常处理工具模块，提供异常信息捕获、打印、错误对象转换等简化异常处理的方法实现
- [call_chain_tool](base_tools/call_chain_tool.md) : 调用链日志处理工具, 提供函数、接口调用链的日志输出相关方法

### simple系列模块

#### simple_cache

[simple_cache](simple_cache.md)定义了一个通用的缓存处理框架类BaseCache，并基于该框架类实现了内存缓存的实现类MemoryCache。

#### simple_i18n

[simple_i18n](simple_i18n.md)是一个简单用于python的多国语言支持的模块，可以根据多国语言信息的配置实现语言的翻译转换。

#### simple_log

[simple_log](simple_log.md)模块重新封装了python的logging模块，提供一个更便于使用的日志处理类。

#### simple_parallel

[simple_parallel](simple_parallel.md)是并行任务（多线程、多进程）的处理框架和实现，包括并行任务处理，以及并行池（类似线程池或进程池）管理的封装，同时该框架可以支持扩展为分布式的并行任务处理（按框架定义实现对应的实现类即可）。

#### simple_queue

[simple_queue](simple_queue.md)框架基于Python原生的队列库（queue）的模式定义了队列处理的基本框架类（QueueFw），并基于该框架类，重构了普通队列（MemoryQueue，该对象合并了queue中的Queue、LifoQueue和PriorityQueue），同时考虑对分布式应用所需的网络队列（如各类MQ）提供框架层级的扩展开发支持。

本队列框架支持的方法与Python原生队列的支持的方法完全一致，因此可以直接使用原生队列替代实现队列处理，例如支持多进程访问的multiprocessing.Queue。

此外，框架也进行改造支持了水桶模式（bucket_mode），即可以往队列一直放对象，但当队列已满的情况下自动通过get丢弃前面的对象。

#### simple_server_fw

[simple_server_fw](simple_server_fw.md)是服务启停服务处理的基础框架，用于支持各类服务启停处理的简单代码实现。

#### simple_stream

[simple_stream](simple_stream.md)模块主要定义了python流处理的框架（按流顺序逐个对象进行处理），并基于该框架实现了字符串流的处理类StringStream。

#### simple_id

[simple_id](simple_id.md)模块定义了id序号（流水号）的生成框架，包括id生成源的管理框架，以及id资源池的id获取方法，支持按指定格式生成具有规则的业务流水号。

#### simple_grpc

[simple_grpc](simple_grpc/simple_grpc.md)库对Google的GRpc库进行了封装，简化Python实现rpc调用的编码方式。

#### simple_console

[simple_console](simple_console.md)是简单的命令行执行框架，可在该框架上基于xml配置文件扩展增加不同的命令支持。

#### simple_webdriver

simple_webdriver 对 selenium WebDriver进行了简单封装，可以快速创建WebDriver对象并基于步骤数组进行元素查找和界面操作执行。



### 其他模块

#### formula

[formula](formula.md)模块可用于对一段文本进行关键字解析，以及进行公式（表达式）匹配和公式值计算。主要应用场景包括代码解析结构化处理（例如将html代码按标签解析为字典形式进行处理）、对一段文本进行自定义公式识别和计算处理。

#### prompt_plus

[prompt_plus](prompt_plus.md)是基Python语言开发的一个增强的交互命令行扩展处理库，基于[prompt_toolkit](https://github.com/jonathanslenders/python-prompt-toolkit)进行封装和扩展，简化需要命令行交互所需要的代码量，不需要了解prompt_toolkit的过多参数设置即可通过数组参数实现命令行和参数的高亮显示和提示输入。

如果您需要了解prompt_toolkit的使用可查看相关文档：http://python-prompt-toolkit.readthedocs.io/en/master/

#### redirect_stdout

[redirect_stdout](redirect_stdout.md)模块由于重定向标准输出的处理，支持将界面的标准输出（print）重定向到其他多个输出对象，例如控制台、字符串、字符数组、日志、文件等，同时该框架也支持进行重定向对象的扩展，以实现更多的标准输出处理功能。

#### net_service

[net_service](net_service/net_service_fw.md)网络服务框架定义了一个标准的网络服务模型，并封装实现了部分网络服务启动、关闭、监听请求及调度具体请求处理线程的功能，以统一网络服务的标准使用方式，以及简化网络服务的开发工作。

在该框架下分别实现了TCP和HTTP服务模型。

#### interface_tool

[interface_tool](interface_tool/msg_fw.md)主要定义了接口报文处理的基础框架：

msg_fw接口报文处理框架定义了一个通用的接口报文需要实现的方法，便于兼容扩展各类报文处理。

IntfMsgFW（接口通讯信息处理框架）定义所有的接口信息必定有两类报文信息：协议信息（例如Http头部分的信息）和报文信息（例如具体的报文内容）。

#### connection_pool

[connection_pool](connection_pool/connection_pool.md)连接池服务框架定义了标准的连接池处理模型，可基于该模型实现数据库、网络连接的连接池。

#### html_parser

html_parser是基于simple_xml实现的html代码解析模块，提供按操作步骤数组逐层向下解析元素的方法，同时解析获取到的元素对象（HtmlElement）的操作方法与 selenium 的 大部分方法兼容。

#### file_transfer

[file_transfer](file_transfer/file_transfer.md)库实现了文件传输（本地或网络）的基本框架，支持快速扩展不同通讯协议下的文件传输功能。

