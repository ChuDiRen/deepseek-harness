"""raw{NN}.json 落盘器。

按 raw01 / raw02 / ... 顺序自动编号，支持按 host 自动分文件（--auto-split-by-domain）。
线程安全。
"""
import json
import threading
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse


class FlowSaver:
    """线程安全的 raw 文件落盘器。"""

    def __init__(
        self,
        batch_dir: str,
        raw_index_start: int = 1,
        exclude_patterns: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None,
        auto_split_by_domain: bool = False,
        flush_threshold: int = 1,
    ):
        self.batch_dir = Path(batch_dir)
        self.batch_dir.mkdir(parents=True, exist_ok=True)
        self.exclude = exclude_patterns or []
        self.include = include_patterns or []
        self.auto_split = auto_split_by_domain
        self.flush_threshold = flush_threshold

        self._lock = threading.Lock()
        self._current_index = raw_index_start
        self._buffer: list = []
        self._host_to_index: dict = {}
        self._host_to_buffer: dict = {}
        self._file_count = 0
        self._total_count = 0
        self._error_count = 0

    # ---------- 公开方法 ----------

    def add(self, record: dict) -> None:
        """接收一条 raw dict。"""
        with self._lock:
            self._total_count += 1
            if record["response"].get("status", 0) == 0:
                self._error_count += 1

            if self.auto_split:
                host = urlparse(record["request"]["url"]).netloc or "unknown"
                if host not in self._host_to_index:
                    self._file_count += 1
                    self._host_to_index[host] = self._file_count
                    self._host_to_buffer[host] = []
                self._host_to_buffer[host].append(record)
                if len(self._host_to_buffer[host]) >= self.flush_threshold:
                    self._flush_host_locked(host)
            else:
                self._buffer.append(record)
                if len(self._buffer) >= self.flush_threshold:
                    self._flush_locked()

    def flush_pending(self) -> None:
        """主流程结束时调用，把所有还在内存的 buffer 落盘。"""
        with self._lock:
            if self.auto_split:
                for host in list(self._host_to_buffer.keys()):
                    self._flush_host_locked(host)
            else:
                self._flush_locked()

    def stats(self) -> dict:
        with self._lock:
            return {
                "files": self._file_count + (1 if self._buffer else 0),
                "total": self._total_count,
                "errors": self._error_count,
            }

    # ---------- 内部方法（必须持有锁） ----------

    def _flush_locked(self) -> None:
        if not self._buffer:
            return
        path = self.batch_dir / f"raw{self._current_index:02d}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(self._buffer, f, ensure_ascii=False, indent=2)
        self._buffer.clear()
        self._current_index += 1
        self._file_count += 1

    def _flush_host_locked(self, host: str) -> None:
        buf = self._host_to_buffer.get(host, [])
        if not buf:
            return
        path = self.batch_dir / f"raw{self._host_to_index[host]:02d}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(buf, f, ensure_ascii=False, indent=2)
        buf.clear()