# bigbear-device-record 发布流程

完全沿用 bigbear-web-record-cli 的加密发布流程（PyArmor + Nexus pypi）。

## 环境要求

```bash
pip install build twine pyarmor
```

## 1. 构建 wheel

```bash
cd bigbear-device-record
rm -rf dist build src/bigbear_device_record.egg-info
python -m build
```

## 2. 加密（PyArmor）

```bash
# 计算 7 天后的过期日期
EXP=$(python -c "from datetime import datetime, timedelta; print((datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'))")
echo "Expiry: $EXP"

pyarmor gen -e "$EXP" -O dist/bigbear_device_record_encrypted -r src
```

## 3. 重新打包 wheel（关键步骤）

```bash
cd dist
python -m zipfile -e bigbear_device_record-1.0.0-py3-none-any.whl encrypted_wheel/
rm -f encrypted_wheel/bigbear_device_record/*.py
cp -r bigbear_device_record_encrypted/src/bigbear_device_record/* encrypted_wheel/bigbear_device_record/
cp -r bigbear_device_record_encrypted/pyarmor_runtime_000000 encrypted_wheel/bigbear_device_record/
cd encrypted_wheel
python -m zipfile -c ../bigbear_device_record-1.0.0-py3-none-any.whl .
cd ..
rm -rf encrypted_wheel bigbear_device_record_encrypted
```

## 4. 上传到 Nexus

```bash
PYTHONIOENCODING=utf-8 PYTHONLEGACYWINDOWSSTDIO=utf-8 NO_COLOR=1 \
  python -m twine upload --repository test --config-file ~/.pypirc \
  dist/bigbear_device_record-1.0.0-py3-none-any.whl
```

## 5. 验证

```bash
pip install bigbear-device-record --extra-index-url http://pypi.hctestedu.com/repository/test/simple/ --trusted-host pypi.hctestedu.com
bigbear-device-record --help
```

## 配置 pypirc

参考 bigbear-web-record-cli 的 `deploy.md`。
