# BigBear Web CLI 安装与升级

> **提示**：仅在需要安装或升级时查看此文档。正常运行不需要查阅此文件。

## pip 镜像源配置（可选，提升下载速度）

推荐配置 pip 镜像源，创建或编辑 `~/.pip/pip.conf`（Linux/Mac）或 `%USERPROFILE%\pip\pip.ini`（Windows）：

```ini
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple/
trusted-host = pypi.tuna.tsinghua.edu.cn
```

**说明**：`bigbear-web-cli` 发布在私有源，依赖包（如 loguru）需从主源获取。建议同时配置主源和私有源（见下方命令）。

## bigbear-web-cli 安装与升级

**首次安装：**
```bash
pip install bigbear-web-cli -i https://pypi.tuna.tsinghua.edu.cn/simple/ --extra-index-url http://public:publicpublic@pypi.hctestedu.com/repository/test/simple/ --trusted-host pypi.hctestedu.com
playwright install chromium
```

**升级到最新版本：**
```bash
pip install --upgrade bigbear-web-cli -i https://pypi.tuna.tsinghua.edu.cn/simple/ --extra-index-url http://pypi.hctestedu.com/repository/test/simple/ --trusted-host pypi.hctestedu.com
```

**安装指定版本：**
```bash
pip install bigbear-web-cli==1.0.1 -i https://pypi.tuna.tsinghua.edu.cn/simple/ --extra-index-url http://pypi.hctestedu.com/repository/test/simple/ --trusted-host pypi.hctestedu.com
```

> **说明**：`-i` 指定主源（清华/腾讯/阿里云等），`--extra-index-url` 添加私有源。pip 会优先从主源查找依赖，私有源找不到的包会回退到主源。

**检查当前版本：**
```bash
bigbear-web-cli --version
```

> **重要提示**：CLI 程序升级后，必须执行 `pip install --upgrade` 才能使新版本生效。仅升级 pyproject.toml 中的版本号不会自动更新已安装的程序。

## playwright-cli 安装与升级

**首次安装：**
```bash
pip install playwright-cli -i https://pypi.tuna.tsinghua.edu.cn/simple/ --extra-index-url http://pypi.hctestedu.com/repository/test/simple/ --trusted-host pypi.hctestedu.com
```

**升级到最新版本：**
```bash
pip install --upgrade playwright-cli -i https://pypi.tuna.tsinghua.edu.cn/simple/ --extra-index-url http://pypi.hctestedu.com/repository/test/simple/ --trusted-host pypi.hctestedu.com
```

**检查当前版本：**
```bash
playwright-cli --version
```

## 依赖项

两个 CLI 工具的依赖：
- `playwright` - 浏览器自动化框架
- `openai` - AI API 调用
- `python-dotenv` - 环境变量管理

## Windows 中文输出

在 Windows 上运行前建议设置环境变量以正确显示中文：

```bash
set PYTHONIOENCODING=utf-8
bigbear-web-cli --port 9222 start
```

或创建一个批处理文件 `bigbear-web.bat`：

```bat
@echo off
set PYTHONIOENCODING=utf-8
bigbear-web-cli %*
```
