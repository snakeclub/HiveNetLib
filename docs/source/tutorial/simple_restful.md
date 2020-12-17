# simple_restful使用说明

simple_restful包模块提供一个基于Flask的易于使用的Restful API发布框架，支持快速实现Restful API服务对外发布，以及实现API服务的安全鉴权能力。



## 创建RestFul API的主要步骤

**1、开发API接口的实际处理类**

类的每个函数用于映射为一个RestFul API，示例如下：

```
from flask import request, jsonify

class StaticAPI(object):
	@classmethod
	def api1(cls, para1:str, para2:int):
		...
		return jsonify(_python_obj)
	
	@classmethod
	def api2(cls, para1:str, methods=['GET'], ver='0.5'):
		...
		return jsonify(_python_obj), 200

class InstanceAPI(object):
	def __init__(self, **kwargs):
		...
		
	def api1(self, para1:str, para2:int):
		...
		return jsonify(_python_obj), 200
```

具体说明如下：

（1）API接口类可支持静态函数类和需实例化执行函数类两种，根据实际需要进行类的创建；如果是实例化执行函数类，需要进行实例化得到类实例对象；

（2）类中的每个非 “_” 开头的函数将会映射为一个API接口；

（3）支持函数入参中通过 methods=["GET"] 指定API支持的 HTTP 动作, 默认为 GET, 一个函数也可以支持多个动作，例如指定 methods=["GET", "POST"] ；

（4）支持函数入参中通过 ver 参数指定api支持版本号，例如 ver='0.5' ；如果遇到指定版本号的情况，也可以指定同时创建一个非版本号访问的路由；

（5）函数的其他入参将按顺序映射至访问 url 路由中，注意不支持 *args/**kwargs 这类动态参数，同时也不支复杂的非基础入参类型（如 dict / list 等类型）；以上例子映射的 url 访问路由如下：

```
# StaticAPI类
Rule('/api/StaticAPI/api1/<string:para1>/<int:para2>', endpoint='StaticAPI.api1',  methods=['GET'])
Rule('/api/0.5/StaticAPI/api2/<string:para1>', endpoint='StaticAPI.api2',  methods=['GET'])
Rule('/api/StaticAPI/api2/<string:para1>', endpoint='StaticAPI.api2',  methods=['GET'])

# InstanceAPI类
Rule('/api/InstanceAPI/api1/<string:para1>/<int:para2>', endpoint='InstanceAPI.api1',  methods=['GET'])
```

（6）函数的返回应该是一个标准的二元组  (flask.wrappers.Response, 200), 可以在返回时通过 flask.jsonify(_python_obj) 将一般的python对象转换为 Response 对象；但也兼容返回单独返回 Response 对象的情况（状态码默认为200）；函数也支持返回其他python对象的做法，比如 str 或 dict 类型，但并不是所有类型都支持，因此建议统一返回  Response 对象的做法；

（7）函数内部可以使用以下方法获取传入参数：

- 通过request.args['key']，获取'?key=value&key1=value1'这类的传参

- 通过request.json['key']，获取在body传入的json结构对应的key的值，例如

- request.json['id']可以获取body中的“{"id": 1234, "info": "测试\\n一下"}” 的id的值

  **注意：报文头的Content-Type必须为application/json**

- 通过request.files['file']，获取上传的文件

**2、实例化鉴权对象（如果不需要鉴权可不做）**

通过鉴权模块可以对请求的安全权限进行判断，一个服务可以支持多个鉴权对象，可以组合使用支持多种鉴权；可支持的鉴权类详见 HiveNetLib.simple_restful.auth 里的类，例如以下代码进行IP黑白名单的鉴权：

```
from HiveNetLib.simple_restful.auth import IPAuth

_ip_auth = IPAuth(
	init_blacklist=['132.159.16.3', '192.168.*.*']  # 初始化IP黑名单
)
```

**4、在接口类的实际函数上增加鉴权修饰符（如果不需要鉴权可不做）**

可以支持三种添加鉴权修饰符的方法：

（1）直接通过鉴权实例对象方式进行函数修饰

优点是可以多个不同的Flask服务共用一个鉴权对象；缺点是鉴权对象的实例化代码必须放在模块的全局代码

```
_ip_auth = IPAuth(
	init_blacklist=['132.159.16.3', '192.168.*.*']  # 初始化IP黑名单
)

class ApiClass(object):
	@classmethod
	@_ip_auth.auth_required
	def login(cls, login:str):
		...
```

（2）通过 FlaskTool.auth_required 动态指定，并通过预定义的 get_auth_fun 函数指定鉴权对象

优点是鉴权对象可以后续代码中再进行创建，修饰符可以先加上; 缺点是 get_auth_fun 函数必须预先定义：

```
from HiveNetLib.simple_restful.server import FlaskTool

def get_auth_fun(auth_name:str=''):
	...
	return _auth

class ApiClass(object):
	@classmethod
	@FlaskTool.auth_required(get_auth_fun=get_auth_fun, get_auth_para={'auth_name':'abc'})
	def login(cls, login:str):
		...
```

（3）通过 FlaskTool.auth_required 动态指定

优点是鉴权对象可以跟着实际Flask服务一起在代码中实例化，修饰符可以先加上；缺点是必须预先设定号 FlaskServer 的名称和鉴权对象的访问名称：

```
from HiveNetLib.simple_restful.server import FlaskTool, FlaskServer

class ApiClass(object):
	@classmethod
	@FlaskTool.auth_required(
		get_auth_fun=FlaskServer.get_logger_fun, 
		get_auth_para={'auth_name': 'IPAuth', 'app_name': 'test_server'}
	)
	def login(cls, login:str):
		...
```

**5、实例化 FlaskServer 服务对象，加载API接口类（或对象）**

```
# 实例化 FlaskServer 服务对象
_sever = FlaskServer(
    'test_server',  # 服务名
    server_config={
        'debug': True,
        'flask_run': {
            'host': '127.0.0.1', 'port': 5000
        },
    },  # 服务配置
    support_auths={
        'IPAuth': _ip_auth, 'AppKeyAuth': _apk_auth
    },  # 支持的鉴权对象
    logger=LOGGER  # 日志
)

# 加载API接口类（或对象）
_sever.add_route_by_class([StaticAPI, _instance_api_obj])
```

**6、启动 FlaskServer 服务**

```
# 可以选择是同步（当前线程阻塞）或异步（函数直接返回）方式启动服务
# 如果是异步服务的方式，可以支持 _sever.stop() 停止服务
_sever.start(is_asyn=True)
```



## FlaskServer高阶用法

通过设置FlaskServer的参数，可以实现一些定制化的功能，简要说明如下：

**1、通过服务启停通知函数实现服务状态的通知处理**

FlaskServer的初始化参数支持传入 before_server_start、after_server_start、before_server_stop、after_server_stop 四个通知函数，可以利用这四个函数实现状态的处理。

例如：在 after_server_start 进行接口服务的注册，在 before_server_stop 进行接口服务的取消注册，以此实现分布式服务启停通知。



## FlaskTool模块应用

FlaskTool 模块为 API 提供一些常用的修饰符，可以简化接口类的编码复杂度，主要功能包括：

**1、支持非 Respone 对象的返回值: FlaskTool.support_object_resp**

该函数支持将接口函数的返回值转换为标准的返回值二元组，这样接口函数可以随意返回标准的python对象即可（**注意：该函数请放在所有修饰符的最下面**）：

```
@classmethod
@FlaskTool.support_object_resp
def login(cls, login:str):
	...
	return {'login': login}
```

**2、支持接口调用链日志记录: FlaskTool.log**

该函数支持记录（或打印）函数接口调用的调用链日志记录，包括服务请求日志和返回报文日志：

```
@classmethod
@FlaskTool.log(
	get_logger_fun=get_logger_fun  # 通过指定函数获取记录日志的logger对象
)
def login(cls, login:str, **kwargs):
	...
	return jsonify({'login': login})
```

注意：

- 为了保证打印最准确的输入输出信息，该概述请放在所有修饰符的最上面；
- 该函数会将 logger, logger_extra, logging_level 等参数传入被修饰的函数，因此请确保被调用函数有这些入参，或者直接增加 **kwargs 参数定义保证调用正常。

**3、支持接口调用连接数据库: FlaskTool.db_connect**

该函数支持在调用服务时连接数据库返回连接对象，以及使用完成关闭数据库连接：

```
@classmethod
@FlaskTool.db_connect(
	db_connect_fun=db_connect_fun  # 通过指定函数获取可用的数据库连接
)
def login(cls, login:str, **kwargs):
	...
	return jsonify({'login': login})
```

注意：该函数会将 db_connection 参数传入被修饰的函数，因此请确保被调用函数有这个入参，或者直接增加 **kwargs 参数定义保证调用正常。

**4、支持服务调用鉴权: FlaskTool.auth_required**

该函数支持对调用服务进行安全上的鉴权处理，如IP限制，报文签名检查等，具体用法已在《创建RestFul API的主要步骤》的《4、在接口类的实际函数上增加鉴权修饰符》中有说明。




## 鉴权模块详解

### IPAuth

IPAuth 模块支持进行 IP 黑白名单的设置和服务访问安全控制，支持的参数如下：

```
@param {list} init_blacklist=None - 初始化的黑名单
    名单可以使用通配符禁止某个网段, 例如 ['127.0.*.*', '138.*.*.*']
@param {list} init_whitelist=None - 初始化的白名单
	名单可以使用通配符只允许某个网段, 例如 ['127.0.*.*', '138.*.*.*']
@param {int} error_resp_status=403 - 验证失败返回状态码
@param {str|dict} error_resp_msg={'status': '10409', 'msg':'IP地址验证失败'} - 验证失败返回的信息
@param {str} interface_id_name='' - 接口id的参数名，如果为''则代表返回错误时不需要返回请求接口id
```

控制逻辑如下：如果有设置白名单，访问IP没有匹配上白名单则拒绝，匹配上则继续进行黑名单判断；如果访问IP匹配上黑名单则拒绝。

除鉴权修饰符函数外，该模块还提供了以下的工具函数：

- verify_blacklist : 检查IP是否在黑名单清单中
- verify_whitelist : 检查IP是否在白名单清单中
- add_blacklist : 添加黑名单
- remove_blacklist : 删除指定黑名单
- clear_blacklist : 清除所有黑名单
- add_whitelist : 添加白名单
- remove_whitelist : 删除指定白名单
- clear_whitelist : 清除所有白名单

### AppKeyAuth

AppKeyAuth 支持 app_id, app_key, app_secret 模式的验证方案

#### 整体验证流程

**调用方对请求报文签名 -> 服务方验证请求签名 -> 服务方处理并对返回报文签名 -> 调用方验证返回报文签名**

**详细说明如下:**

1. 服务端生成APP信息，线下提供给商户

​      AppId: 商户id

​      AppKey: 公匙（相当于账号）

​      AppSecret: 私匙（相当于密码）

2. 客户端对要发送的数据进行签名，算法如下:

​    (1) 客户端生成 nonce_str 随机字符串, 例如: 'ibuaiVcKdpRxkhJA'

​    (2) 设要发送的数据为集合M，将所有非空参数值的参数按照参数名ASCII码从小到大排序（字典序），

​    使用URL键值对的格式（即key1=value1&key2=value2…）拼接成字符串stringA, 例如:

​      stringA="body=test&device_info=1000&mch_id=10000100"

​    (3) 拼接API密钥

​      \# 拼接app_id、app_key、app_secret、nonce_str、timestamp进入签名字符串

 stringSignTemp = stringA+"&app_id=1333&app_key=123456&app_secret=192006250b4c09247ec02edce69f6a2d&nonce_str=xx&timestamp=xx"

​      \# 如果选择MD5签名方式, 处理及得到结果如下

​      sign=MD5(stringSignTemp).toUpperCase()="9A0A8659F005D6984697E2CA0A9CF3B7"

​      \# 如果选择HMAC-SHA256算法签名方式，处理及得到结果如下

​      \# 注意：部分语言的hmac方法生成结果二进制结果，需要调对应函数转化为十六进制字符串。

​     sign = hash_hmac("sha256",stringSignTemp,AppSecret).toUpperCase()="6A9AE1657590FD6257D693A078E1C3E4BB6BA4DC30B23E0EE2496E54170DACD6"

​    (4) 将sign放入要发送的数据集合中，客户端调用api接口

​    (5) 服务器端同样做相应算法的认证sign生成，并进行比对检查

#### AppKey管理

AppKeyAuth 内部自带了一个简单版的 AppKey管理功能，可以通过以下 3 个函数进行 AppKey 的管理：

- apk_generate_key_pair : 指定 AppId 生成一个 AppKey, AppSecret 密钥对, 同时存入内存管理库中
- apk_update_secret :  将指定的 AppId, AppKey, AppSecret 存入内存管理库中
- apk_get_secret_fun : 根据 AppId 从内存管理库获取对应的 AppKey, AppSecret 密钥对

使用 AppKeyAuth 时会默认使用自带的 AppKey 管理功能，如果想要使用自定义的 AppKey 管理功能，可以在初始化鉴权模块时指定获取 AppKey, AppSecret 密钥对的函数：

```
# 自定义获取密钥对的函数
def my_get_secret_fun(app_id:str) -> tuple:
	...
	return (app_key, app_secret)

# 初始化时指定获取密钥对函数
_auth = AppKeyAuth(
	get_secret_fun=my_get_secret_fun
)
```

#### 自定义算法扩展

自带的签名算法支持 MD5 和 HMAC-SHA256 两种，也可以通过自定义算法函数的方式增加其他算法的支持，具体方法如下：

```
# 新建算法函数
def algorithm_fun(value:str, key:str) -> str:
	...

# 在初始化鉴权模块时将算法加入算法扩展参数
_auth = AppKeyAuth(
	algorithm='NewAlgorithm', algorithm_extend={'NewAlgorithm': algorithm_fun}
)
```

