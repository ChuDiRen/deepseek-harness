# bigbear-web-record 发布流程

## 环境要求
```bash
pip install build twine
```

---

## 模式一：非加密源码发布

### 1. 构建 wheel 包
```bash
cd d:/work/course/test/ai_test/test_opc/bigbear-web-record
rm -rf dist build src.egg-info
python -m build
```

### 2. 上传到 Nexus 私有仓库
```bash
PYTHONIOENCODING=utf-8 PYTHONLEGACYWINDOWSSTDIO=utf-8 NO_COLOR=1 python -m twine upload --repository test --config-file ~/.pypirc dist/bigbear_web_record-1.0.0-py3-none-any.whl
```

### 3. 验证发布
```bash
curl -s -u upload:bigbearupload. "http://192.168.1.6:18081/service/rest/v1/components?repository=test" | python -c "import sys,json; data=json.load(sys.stdin); [print(i['name'], i['version'], [a['path'] for a in i['assets']]) for i in data['items']]"
```

### 4. 安装验证
```bash
pip install bigbear-web-record --extra-index-url http://pypi.hctestedu.com/repository/test/simple/ --trusted-host pypi.hctestedu.com
```

---

## 模式二：加密源码发布（仅 wheel，无源码）

### 1. 构建 wheel 包
```bash
cd d:/work/course/test/ai_test/test_opc/bigbear-web-record
rm -rf dist build src.egg-info
python -m build
```

### 2. 使用 PyArmor 加密（7 天有效期示例，有效期到 2026-05-11）
```bash
# 计算过期日期
python -c "from datetime import datetime, timedelta; print((datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'))"

# 加密 src 目录
pyarmor gen -e 2026-05-11 -O dist/bigbear_web_record_encrypted -r src
```

### 3. 重新打包为 wheel（关键步骤）
```bash
cd dist

# 解压原始 wheel 到新目录（不能用遗留目录名）
python -m zipfile -e bigbear_web_record-1.0.0-py3-none-any.whl encrypted_wheel/

# 【重要】先删除原始 .py 文件，防止源码残留
rm -f encrypted_wheel/bigbear_web_record/*.py

# 复制加密文件替换原始文件
cp -r bigbear_web_record_encrypted/src/bigbear_web_record/* encrypted_wheel/bigbear_web_record/

# 复制 pyarmor 运行时
cp -r bigbear_web_record_encrypted/pyarmor_runtime_000000 encrypted_wheel/bigbear_web_record/

# 重新打包
cd encrypted_wheel
python -m zipfile -c ../bigbear_web_record-1.0.0-py3-none-any.whl .

# 返回上级目录
cd ..

# 验证 whl 内容（检查是否只有一套代码，无原始源码）
python -m zipfile -l bigbear_web_record-1.0.0-py3-none-any.whl | grep "\.py$"

# 清理临时文件（注意：encrypted_wheel 可能被占用，稍后清理）
rm -rf encrypted_wheel bigbear_web_record_encrypted
```

### 4. 验证打包结果
```bash
# 检查 whl 中只有一套 .py 文件，且包含 pyarmor_runtime
python -m zipfile -l dist/bigbear_web_record-1.0.0-py3-none-any.whl

# 正确输出示例（只有一套代码，无原始源码）：
# bigbear_web_record/__init__.py
# bigbear_web_record/__main__.py
# bigbear_web_record/cli.py
# bigbear_web_record/generator/__init__.py
# bigbear_web_record/generator/markdown_docs.py
# bigbear_web_record/parser/__init__.py
# bigbear_web_record/parser/dependency_analyzer.py
# bigbear_web_record/parser/request_parser.py
# bigbear_web_record/recorder/__init__.py
# bigbear_web_record/recorder/browser.py
# bigbear_web_record/recorder/floating_ball.py
# bigbear_web_record/recorder/interceptor.py
# bigbear_web_record/recorder/socket_server.py
# bigbear_web_record/pyarmor_runtime_000000/pyarmor_runtime.pyd
```

### 5. 上传到 Nexus 私有仓库
```bash
PYTHONIOENCODING=utf-8 PYTHONLEGACYWINDOWSSTDIO=utf-8 NO_COLOR=1 python -m twine upload --repository test --config-file ~/.pypirc dist/bigbear_web_record-1.0.0-py3-none-any.whl
```

---

## 删除旧源码包（如有）
```bash
# 查询组件 ID
curl -s -u upload:bigbearupload. "http://192.168.1.6:18081/service/rest/v1/components?repository=test" | python -c "import sys,json; data=json.load(sys.stdin); [print(i['id'], i['name']) for i in data['items']]"

# 删除整个组件
curl -s -u upload:bigbearupload. -X DELETE "http://192.168.1.6:18081/service/rest/v1/components/<组件ID>"
```

---

## PyArmor 加密选项

| 选项 | 说明 |
|------|------|
| `-e YYYY-MM-DD` | 设置过期日期 |
| `-O PATH` | 输出目录 |
| `-r` | 递归加密子目录 |

---

## 配置 pypirc (~/.pypirc)
```ini
[test]
username = upload
password = bigbearupload.
repository = http://192.168.1.6:18081/repository/test/

[distutils]
index-servers = test
```

---

## 常见问题

### PyArmor 无效日期格式
```bash
# 错误：+7d 不支持
pyarmor gen -e +7d ...

# 正确：计算具体日期
python -c "from datetime import datetime, timedelta; print((datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'))"
pyarmor gen -e 2026-05-11 ...
```

### twine 上传 UnicodeEncodeError / rich 进度条错误
Windows 上传时 twine 使用 rich 库显示进度条，在 GBK 编码的控制台会报错：
```
UnicodeEncodeError: 'gbk' codec can't encode character '•'
```
**解决方法**：设置编码环境变量或禁用颜色：
```bash
# 方法一：设置编码（推荐）
export PYTHONIOENCODING=utf-8
TWINE_USERNAME=upload TWINE_PASSWORD=bigbearupload. python -m twine upload -r test dist/*

# 方法二：禁用颜色输出
PYTHONIOENCODING=utf-8 PYTHONLEGACYWINDOWSSTDIO=utf-8 NO_COLOR=1 python -m twine upload ...
```

### 删除源码包
Nexus 中 wheel 和 tar.gz 在同一组件，需删除整个组件后重新上传 wheel。

### whl 中仍有原始源码
打包时必须先删除原始 .py 文件再复制加密文件，且解压目录不能与之前重复。

### visual-cpp-build-tools
Microsoft Visual C++ 14.0 or greater is required. Get it with "Microsoft C++ Build Tools": https://visualstudio.microsoft.com/visual-cpp-build-tools/