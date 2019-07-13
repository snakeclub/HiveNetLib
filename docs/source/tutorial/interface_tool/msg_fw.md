# msg_fw接口报文处理框架

msg_fw接口报文处理框架定义了一个通用的接口报文需要实现的方法，便于兼容扩展各类报文处理。



## 基础报文信息处理框架类（MsgFW）

### 构造函数（\_\_init\_\_)

几个重要参数说明（详细说明请参看接口文档）

obj : 要装载的报文载体（与obj_type结合来判断是什么对象），例如(仅供参考)：

- obj_type = EnumMsgObjType.File 时，obj为文件路径
- obj_type = EnumMsgObjType.FileHandle 时，obj为文件句柄
- obj_type = EnumMsgObjType.String 时，obj为报文文本

msg_id : 报文id，用于标明该报文是什么业务报文，例如都是json格式的报文，但在使用时需区分是什么业务报文

kwargs : 装载参数，根据实现类的需要传入具体的参数，例如传入字符编码encoding='utf-8'

**通过构造函数可以将各种格式的报文（文本、字节流、文件、文件句柄）转换为可执行标准处理的报文实例对象。**



### 公共属性

**msg.base_object**

获取报文转换后的基础处理对象，处理对象类型由实现类定义；例如xml报文，报文将转换为lxml库的xml document对象，获取该基础处理对象可以自行实现各类操作处理

**msg.msg_id**

获取报文ID（定义是什么报文）

**msg.msg_type**

返回消息对象的类型（字符格式），需实现类重载返回正确的类型名



### 公共函数 - 子报文操作

**msg.append_submsg**

添加子报文信息，将子报文对象（MsgFW实例）添加到当前报文实例的指定路径中（search_path）

**msg.append_submsg_by_base_object**

添加子报文信息，将子报文对象（基础处理对象，例如MsgFW.base_object）添加到当前报文实例的指定路径中（search_path）

**msg.append_submsg_by_object**

添加子报文信息，将子报文对象（未转换的任意类型，例如文本或文件）添加到当前报文实例的指定路径中（search_path）

**msg.get_value**

获取报文指定路径（search_path）的内容值

**msg.set_value**

设置报文指定路径（search_path）的内容值

**msg.to_str**

将报文实例转换为字符串格式

**self.to_bytes**

将报文实例转换为二进制数组



### 需重载的内部函数

**self._load_msg**

装载报文对象,将传入的报文对象转换为基础处理对象（例如xml报文的报文对象指xml document对象）

**self._append_submsg**

将子报文对象添加到主报文对象中，并返回主报文对象，注意所提到的报文对象均为基础处理对象（例如xml报文的报文对象指xml document对象），非MsgFW的实例对象

**self._get_msg_value**

获取报文指定路径（search_path）的内容值，所传入的报文对象为基础处理对象（例如MsgFW.base_object）

**self._set_msg_value**

设置报文指定路径（search_path）的内容值，所传入的报文对象为基础处理对象（例如MsgFW.base_object）

**self._msg_to_str**

将指定报文对象（基础处理对象，例如MsgFW.base_object）转换为字符串

**self._msg_to_bytes**

将指定报文对象（基础处理对象，例如MsgFW.base_object）转换为二进制数组



### 实现自定义接口报文处理类

注意：框架里的搜索路径（search_path）可以根据实现类的需要自定义，但建议统一参考xPath的格式，便于不同报文类型的适配



目前已基于该接口框架实现了以下几类标准格式报文的处理类：

- msg_xml.MsgXML : XML报文信息处理类
- msg_json.MsgJSON ：JSON报文信息处理类
- protocol_msg_http.MsgHTTP : HTTP协议报文信息处理类(处理http协议的标准报文头)



## 接口通讯信息处理框架（IntfMsgFW）

定义所有的接口信息必定有两类报文信息：协议信息（例如Http头部分的信息）和报文信息（例如具体的报文内容）

框架内容较为简单，可以直接参考代码