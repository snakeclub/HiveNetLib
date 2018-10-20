# 使用simple_i18n

simple_i18n是一个简单用于python的多国语言支持的模块，可以根据多国语言信息的配置实现语言的翻译转换。

## 多国语言信息配置格式说明

simple_i18n的多国语言配置采用JSON的语言格式，配置信息可以通过文件导入、JSON字符串导入，或直接导入JSON对象。每一个国家语言配置为一个独立的JSON对象，格式如下：

```JSON
{
	"msg_id 1" : "msg_str 1",
	"msg_id 2" : "msg_str 2",
	...
}
```

msg_id为要翻译语言的标识字符串，唯一确定要翻译的内容，多个不同国家语言的msg_id应统一，建议msg_id直接使用英语（en）提示内容，以保证代码的可读性。

msg_str为对应msg_id的翻译内容，根据不同国家语言配置不同的内容。需注意的是msg_str支持占位符的方式，用于替换一些变量值，占位符格式为"$+顺序号"，例如"$2"代表该占位符需要替换第2个变量。

占位符的使用例子如下：

```
'my name is $1, i am $2 years old. '
翻译时传入的变量可以为：('lhj', 30)
翻译后的结果为：'my name is lhj, i am 30 years old. '
```



## SimpleI18N类使用说明

SimpleI18N类是多国语言支持的基础类，用于管理多国语言配置信息和执行翻译处理，可以生成多个SimpleI18N类来处理不同的翻译需求。

SimpleI18N的使用步骤如下：

1、初始化SimpleI18N类

```
i18n_obj = SimpleI18N(lang='zh', trans_file_path='c:/test/', trans_file_prefix='test',
                 encoding='utf-8', auto_loads=True)
```

lang设置该类的默认翻译国家语言

auto_loads参数定义是否初始化时通过文件自动加载语言配置，如果auto_loads为True，初始化自动从trans_file_path目录下，寻找文件格式为"{trans_file_prefix}_{lang}.json"的文件进行加载。

例如上例中如果“c:/test/”目录下有"test_en.json"、“test_zh.json”文件，则会自动加载这两个语言的配置文件。



2、补充或替换多国语言配置信息

通过load_trans_from_str、load_trans_from_json或load_trans_from_file维护多国语言配置信息，追加或覆盖，例如：

```
i18n_obj.load_trans_from_str(json_str='{"success!": "成功!"}', lang='zh', append=True)
```



3、在需要的地方执行语言翻译

```
s1 = i18n_obj.translate(msg_id='success!', lang='zh')
s2 = i18n_obj.translate(msg_id='my name is $1, i am $2 years old.',
                        replace_para=('lhj', 30))
```



## 更快捷的翻译使用方式

1、import时显示导入快捷函数（注意快捷函数"_"）

```
from simple_i18n import SimpleI18N, _, set_global_i18n
```



2、初始化一个要全局使用的SimpleI18N对象，并维护相关翻译信息



3、配置全局翻译对象

```
set_global_i18n(i18n_obj)
```



4、在直接需要翻译的地方使用简单模式翻译

```
s6 = _('my name is $1, i am $2 years old. haha！', 'lhj', 30)
```

