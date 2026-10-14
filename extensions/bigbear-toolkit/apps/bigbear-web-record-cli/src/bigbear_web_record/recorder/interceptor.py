from dataclasses import dataclass, field
from typing import List, Dict, Optional
import json
import re

@dataclass
class NetworkRequest:
    id: str
    method: str
    url: str
    headers: Dict[str, str]
    body: Optional[str] = None
    timestamp: float = 0.0

@dataclass
class NetworkResponse:
    request_id: str
    status: int
    headers: Dict[str, str]
    body: Optional[str] = None
    timestamp: float = 0.0

@dataclass
class RecordedFlow:
    request: NetworkRequest
    response: NetworkResponse

# Default static resource patterns to filter
DEFAULT_STATIC_PATTERNS = [
    r'\.js(\?.*)?$',
    r'\.css(\?.*)?$',
    r'\.html?(\?.*)?$',
    r'\.png(\?.*)?$',
    r'\.jpg(\?.*)?$',
    r'\.jpeg(\?.*)?$',
    r'\.gif(\?.*)?$',
    r'\.svg(\?.*)?$',
    r'\.ico(\?.*)?$',
    r'\.woff2?(\?.*)?$',
    r'\.woff(\?.*)?$',
    r'\.ttf(\?.*)?$',
    r'\.eot(\?.*)?$',
    r'\.webp(\?.*)?$',
    r'\.mp4(\?.*)?$',
    r'\.webm(\?.*)?$',
    r'\.mp3(\?.*)?$',
    r'\.wav(\?.*)?$',
    r'\.pdf(\?.*)?$',
    r'\.zip(\?.*)?$',
    r'\.gz(\?.*)?$',
    r'\.tar(\?.*)?$',
    r'\.rar(\?.*)?$',
    r'favicon',
    r'analytics',
    r'googletagmanager',
    r'google-analytics',
    r'hotjar',
    r'mixpanel',
    r'segment',
    r'mouseflow',
]

class NetworkInterceptor:
    def __init__(self, filter_static: bool = True, additional_exclude_patterns: Optional[List[str]] = None):
        self.requests: List[NetworkRequest] = []
        self.responses: Dict[str, NetworkResponse] = {}
        self.flows: List[RecordedFlow] = []
        self.filter_static = filter_static
        self.exclude_patterns = DEFAULT_STATIC_PATTERNS.copy()
        if additional_exclude_patterns:
            self.exclude_patterns.extend(additional_exclude_patterns)
        self.exclude_regex = [re.compile(p, re.IGNORECASE) for p in self.exclude_patterns]

    def _is_static_resource(self, url: str) -> bool:
        """Check if URL matches static resource patterns"""
        for pattern in self.exclude_regex:
            if pattern.search(url):
                return True
        return False

    def on_request(self, request: NetworkRequest):
        if self.filter_static and self._is_static_resource(request.url):
            return  # Skip static resources
        self.requests.append(request)

    def on_response(self, response: NetworkResponse):
        # Only save response if the corresponding request was captured (not filtered)
        if not any(req.id == response.request_id for req in self.requests):
            return  # Corresponding request was filtered, skip this response
        self.responses[response.request_id] = response

    def build_flows(self):
        for req in self.requests:
            if req.id in self.responses:
                self.flows.append(RecordedFlow(req, self.responses[req.id]))

    def get_flows(self) -> List[RecordedFlow]:
        if not self.flows:
            self.build_flows()
        return self.flows

    def clear(self):
        self.requests.clear()
        self.responses.clear()
        self.flows.clear()

    def save_flows_to_file(self, output_path: str) -> int:
        """Save current flows to JSON file, return number of flows saved."""
        flows = self.get_flows()
        if not flows:
            return 0

        raw_data = []
        for flow in flows:
            raw_data.append({
                "request": {
                    "id": flow.request.id,
                    "method": flow.request.method,
                    "url": flow.request.url,
                    "headers": flow.request.headers,
                    "body": flow.request.body,
                    "timestamp": flow.request.timestamp,
                },
                "response": {
                    "status": flow.response.status,
                    "headers": flow.response.headers,
                    "body": flow.response.body,
                    "timestamp": flow.response.timestamp,
                }
            })

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)

        return len(flows)
