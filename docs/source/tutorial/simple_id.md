# simple_id使用说明

simple_id模块定义了id序号（流水号）的生成框架，包括id生成源的管理框架，以及id资源池的id获取方法，支持按指定格式生成具有规则的业务流水号。

## IdSourceFW框架

IdSourceFW框架定义了Id生成源的标准处理功能。在这个框架中定义了Id生成处理的两类对象，IdSource和IdPool：

- IdSource(Id生成源) :  Id生成源用于管理Id的生成，包括产生唯一的Id段，设置当前Id值等，关注Id源头值的管理，具体的id当前值可以在内存、文件、数据库中存储，需要具体实现类保障所产生Id的唯一性
- IdPool(Id资源池) : Id资源池用于申请Id资源段进入缓存池，并提供应用申请获取具体Id序号的功能，同时提供流水号规则功能，关注于具体id的获取及有规则流水号的生成

注意：该框架针对的id以自然数字的序号为基础，如果需要产生非自然数字的序号，则无法应用框架内置的处理函数，需自行实现框架所需的所有方法

### IdSource公共属性及成员函数介绍

**构造函数** : 初始化Id生成源对象

**allocate(self, size, \*\*kwargs)**

分配指定大小的id序号

```
@param {int} size - 要分配的id数量
@param {kwargs} - 由具体实现类自定义的参数
@return {tuple} - 返回的id序号范围(最小值, 最大值)
	注意：当需要获取的序号范围超过序号限制最大值时，返回的序号范围有可能小于size(只取到最大值)
```

**set_current_id(self, id, \*\*kwargs)**

设置当前id序号

```
@param {int} id - 要设置的id
@param {kwargs} - 由具体实现类自定义的参数
```



### 自定义IdSource实现类

1、实现类需继承IdSourceFw

```
class IdSourceMemory(IdSourceFW):
	...
```

2、实现类必须实现以下几个重载函数

- _init(self, \*\*kwargs) : 自定义的构造函数，这里的kwargs只需关注自定义的入参即可，父类的构造函数入参可以通过self.xxx获取并处理
- _set_current_id(self, id, \*\*kwargs) : 设置当前id的值，父类会基于self.\_lock进行id生成源变更的锁处理，因此该函数无需考虑资源锁问题（注意构造函数会调用这个函数进行当前id的初始值设置，这个时候kwargs传入的是构造函数的kwargs）
- _get_current_id(self, \*\*kwargs) : 获取当前id的值，父类会基于self.\_lock进行id生成源变更的锁处理，因此该函数无需考虑资源锁问题

3、可选，通过个性化以下重载函数实现更灵活的扩展功能支持

- _get_id_operate_lock(self, \*\*kwargs) : 获取id操作锁对象, 函数默认取threading.RLock作为锁对象, 可根据需求更换其他操作锁（例如支持数据库锁、跨进程锁等）；注意返回锁实例对象必须支持with
- _set_is_overflow(self, is_owerflow, \*\*kwargs) : 设置is_owerflow的值, 函数默认设置当前对象的\_is\_owerflow属性，可以根据需求自定义（例如设置远程服务器上的变量）
- _get_is_overflow(self, \*\*kwargs) : 获取is_owerflow的值，与\_set_is_overflow对应





## IdSourceMemory（内存Id生成源）

IdSourceMemory是内存Id生成源的简单实现，Id仅程序运行期间有效，无持久化，不支持跨进程。



## IdPool（Id资源池）的使用

#### 简单使用

1、创建IdSource实例对象

```
_idsource = IdSourceMemory(
	max_id=20, is_circle=True, min_id=1, initial_id=3
)
```

2、初始化IdPool

```
_idpool = IdPool(_idsource, alloc_size=4, alloc_lower_size=2, is_deamon=True)
```

3、在应用中直接获取id

```
_id = _idpool.get_id()
```

#### 高阶使用

利用构造函数可以支持Id的各种高阶使用（例如自定义Id格式，直接获取指定格式的流水号），参数说明如下：

```
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
```



### IdPoolUuid（UUID资源池）

IdPoolUuid是通过uuid产生唯一的ID的资源池实现，兼容IdPool的公共方法。

