# 使用simple_console

simple_console是简单的命令行执行框架，可在该框架上基于xml配置文件扩展增加不同的命令支持，主要特点如下：

1. 支持xml配置不同命令扩展;
2. 支持多国语言显示；
3. 进入控制台可支持命令提示；
4. 支持直接在shell中执行命令，以及执行批量命令文件；
5. 跨平台;



## 使用simple_console开发命令行应用

可以按照以下的大步骤开发您自己的命令行应用：

### 开发扩展命令类

可以基于CmdBaseFW自行开发扩展命令，示例如下：

```
from HiveNetLib.generic import CResult
from HiveNetLib.simple_i18n import _
from HiveNetLib.simple_console.base_cmd import CmdBaseFW

class YourClass(CmdBaseFW):
	#############################
    # 需具体实现类覆盖实现的类
    #############################
    def _init(self, **kwargs):
        """
        实现类需要覆盖实现的初始化函数
        @param {kwargs} - 传入初始化参数字典（config.xml的init_para字典）
        @throws {exception-type} - 如果初始化异常应抛出异常
        """
        您的自定义初始化内容...
        
    def _cmd_dealfun(self, message='', cmd='', cmd_para='', prompt_obj=None, **kwargs):
        """
        实现类需要覆盖实现的命令处理函数
        @param {string} message='' - prompt提示信息
        @param {string} cmd - 执行的命令key值
        @param {string} cmd_para - 传入的命令参数（命令后的字符串，去掉第一个空格）
        @param {PromptPlus} prompt_obj=None - 传入调用函数的PromptPlus对象，可以通过该对象的一些方法控制输出显示
        @param {kwargs} - 传入的主进程的初始化kwargs对象
        @returns {CResult} - 命令执行结果，可通过返回错误码10101通知框架退出命令行, 同时也可以通过CResult对象的print_str属性要求框架进行打印处理
        """
        您自己的处理函数内容
```

关注点如下：

- 通过 self._console_global_para 可以获取命令行框架的公共变量，有用的公共变量包括：
  - execute_file_path ：您的应用程序主目录
  - work_path ： 工作目录，也就是启动命令行的当前目录
- 框架会自动加载i18n控件作为全局多国语言控件，您可以通过"from HiveNetLib.simple_i18n import _"载入方法，并在您的应用打印时进行多国语言转换，具体用法参考simple_i18n的手册
- 您可以在一个类中实现多个命令函数，自行通过“_cmd_dealfun”做逻辑路由即可，可以参考“HiveNetLib.simple_console.base_cmd.CommonCmd”的方法
- “cmd”和“cmd_para” 两个参数将输入的命令传给执行函数；

### 部署您的应用目录

1、请将simple_console下的“conf/config.xml”复制到您的应用目录下，例如"/yourapp/conf/config.xml"；当然您也可以放到不同目录或指定不同文件名，但这样后续需要有些特殊的编码处理；

2、在应用目录下创建 "i18n"目录用于放置多国语言文件；您也可以放到不同目录下，但需要修改config.xml中的 “i18n” 配置指定目录；

3、创建多国语言文件，不同语言的文件名为"message_语言标识.json"，例如"message_en.json"，翻译样式非常简单，就是类似以下格式的json字符串， 详细信息请参考simple_i18n的手册：

```
{
    "'$1' is not support command!": "控制台不支持 '$1' 命令！",
    "You will shutdown $1 Console, continue?(y/N)": "您将关闭 $1 控制台，请确认是否继续(y/N)?",
    "Exit $1 Console": "退出 $1 控制台",
    "Cancel Exit": "取消退出操作"
}
```

4、创建一个用于启动控制台的py文件（例如console.py），用于执行启动操作，代码非常简单：

```
import sys
import os
from HiveNetLib.base_tools.file_tool import FileTool
from HiveNetLib.simple_console.server import ConsoleServer

def main(**kwargs):
    ConsoleServer.console_main(
        execute_file_path=os.path.realpath(FileTool.get_file_path(__file__)),
        **kwargs
    )

if __name__ == '__main__':
    main()
```

注：如果您希望将config放到不同目录，请在console_main函数传入default_config_file参数。

### 配置应用命令

1、所有配置都在config.xml中，一些显示的配置项如下：

- /console/name : 您的应用名称，在帮助文本中可以通过 {{NAME}} 进行替换

- /console/version : 应用版本, 在帮助文本中可以通过 {{VERSION}} 进行替换

- /console/shell_cmd_name: 您的程序建立的系统软连接名称, 在帮助文本中可以通过 {{SHELL_CMD_NAME}} 进行替换

- /console/message : 控制台前面显示的提示符

  

2、将您的扩展命令配置到框架中，您需要在“/console/cmd_list”下新增相应的\<cmd>标签，例如：

```
<cmd>
    <command>mdtowiki</command>
    <module_name>mediawikiTool.lib.mediawiki_cmd</module_name>
    <class_name>MediaWikiCmd</class_name>
    <extend_path/>
    <init_para/>
    <cmd_para>{
        "long_para": {
            "in": [],
            "out": [],
            "name": [],
            "stdpic": []
        }
    }
    </cmd_para>
    <help>{
        "en": [
                "convert markdown file to mediawiki format",
                "",
                "mdtowiki -in file [-out outpath] [-name title] [-stdpic]",
                "    -in : Markdown file path (include filename), if just filename then search on the current working directory",
                "    -out : the MediaWiki file output path, If not specified to represent output on the current working directory",
                "    -name : MediaWiki page title, If you do not specify the filename that represents the use of Markdown filename (without the extension)",
                "    -stdpic : Set this parameter to automatically rename the pictures in order;Otherwise it will be named after the original file name",
                "",
                "demo: mdtowiki -in mdtowiki.md",
                ""
        ],
        "zh_cn": [
                "将markdown格式文件转换为mediawiki格式",
                "",
                "mdtowiki -in file [-out outpath] [-name title] [-stdpic]",
                "    -in : Markdown文件路径(含名称), 如果在当前工作目录下可以只输入名称",
                "    -out : 要输出的MediaWiki文件路径, 如果不指定代表输出在当前工作目录上",
                "    -name : MediaWiki标题名字，如果不指定代表使用Markdown的文件名(不含扩展名)",
                "    -stdpic : 设置该参数可以自动将图片按顺序重命名; 否则将按原文件名命名",
                "",
                "示例: mdtowiki -in mdtowiki.md",
                ""
        ]
    }
    </help>
</cmd>
```

说明如下：

- “command ” 是命令字符，及在命令行中输入的最前面的词
- “module_name” 是您的扩展命令的模块路径及名称，例如正常调用时需要 "import xxx.xxx"，则应填入"xxx.xxx"
- “class_name” 是您的扩展命令所在的类，注意该类必须继承 “CmdBaseFW”
- “extend_path” 是需要sys.path中增加的搜索路径，如果您的代码没有安装，则需要指定路径以找到代码文件
- “init_para” 是扩展的初始化参数，如果您有自定义的初始化参数，可以以json字典的方式传入相关参数
- “cmd_para” 是命令提示的参数，格式可参考prompt_plus
- “help” 是命令的帮助，如上例，可以设置多语言的支持



3、如果您希望不使用"python console.py"这种方式执行，可以修改您的setup.py文件，增加以下参数，让安装的时候直接建立软连接，如以下示例，会建立一个wikitool的软连接直接启动程序，连接到console.py的main函数执行：

```
# 示例
entry_points={'console_scripts': [
    "wikitool = mediawikiTool.console:main"
]},
```



## 使用simple_console框架

1、执行上例中实现的console.py，将进入控制台进行命令的执行，该方式的好处是可以有命令提示；

2、通过传入参数直接在shell中执行内部的命令，具体方式可使用"python console.py help=y"查看。