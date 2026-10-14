"""bigbear-mitmproxy-record recorder 子包。

- addon.py:       mitmproxy addon 入口
- flow_codec.py:  HTTPFlow → raw dict 转换器
- saver.py:       raw{NN}.json 落盘
- webui_monitor.py: 8081 端口探活
"""