# HiveNetLib
HiveNetLib 是一个方便开发人员调用的，集合一些常用开发功能的开发Python库，包括网络编程（tcpip、http）、日志、命令行交互、公式计算等。

HiveNetLib 的目的是让开发人员用最简单的方法实现最常用的功能，提高开发效率，关注具体功能逻辑而非具体技术实现。

同时该库为开源项目HiveNet依赖的基础库。



GitHub：https://github.com/snakeclub/HiveNetLib/

介绍：[HiveNetLib tutorial](docs/source/tutorial/catalog.md)



## 更新记录

### v0.9.0版本（当前库的最后一个版本, 后续不再维护, 相关功能会逐步转移到HiveNetAssemble项目中进行维护）
- 新增simple sanic库
- 扩充base_tools的各个库的功能函数, 新增opentracing_tool
- 废弃原版本的连接池框架, 使用simple_pool替代
- 优化和修复其他库的一些问题

### v0.8.9版本

- 新增 file_transfer 库，封装了文件网络传输的基础功能；
- prompt_plus库新增 ProgressRate 进度值控制、展示处理类
- prompt_plus库PromptPlus类支持获取及更新命令行参数方法
- simple_console库新增加载自定义多国语言文件的支持
- 去掉对affinity库的依赖
- 扩充base_tools的各个库的功能函数
- 修复 simple_grpc 库中 SimpleGRpcServer 无法通过 servicer_list 同时注册多个 SimpleGRpcServicer 的bug

