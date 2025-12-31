"""指标收集和监控"""
from typing import Dict, Optional
from collections import defaultdict
from threading import Lock
from datetime import datetime

from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.utils.metrics")


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self._lock = Lock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._histograms: Dict[str, list] = defaultdict(list)
        self._gauges: Dict[str, float] = {}
        self._start_time = datetime.now()
    
    def increment(self, metric_name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """增加计数器"""
        key = self._format_key(metric_name, labels)
        with self._lock:
            self._counters[key] += value
    
    def record_duration(self, metric_name: str, duration: float, labels: Optional[Dict[str, str]] = None):
        """记录持续时间（秒）"""
        key = self._format_key(metric_name, labels)
        with self._lock:
            self._histograms[key].append(duration)
            # 只保留最近 1000 条记录
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]
    
    def set_gauge(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """设置仪表值"""
        key = self._format_key(metric_name, labels)
        with self._lock:
            self._gauges[key] = value
    
    def get_metrics(self) -> Dict:
        """获取所有指标"""
        with self._lock:
            # 计算直方图统计信息
            histograms_stats = {}
            for key, values in self._histograms.items():
                if values:
                    histograms_stats[key] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "p50": self._percentile(values, 50),
                        "p95": self._percentile(values, 95),
                        "p99": self._percentile(values, 99),
                    }
            
            return {
                "counters": dict(self._counters),
                "histograms": histograms_stats,
                "gauges": dict(self._gauges),
                "uptime_seconds": (datetime.now() - self._start_time).total_seconds(),
            }
    
    def _format_key(self, metric_name: str, labels: Optional[Dict[str, str]]) -> str:
        """格式化指标键"""
        if not labels:
            return metric_name
        label_str = ",".join([f"{k}={v}" for k, v in sorted(labels.items())])
        return f"{metric_name}{{{label_str}}}"
    
    def _percentile(self, values: list, percentile: int) -> float:
        """计算百分位数"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        if index >= len(sorted_values):
            index = len(sorted_values) - 1
        return sorted_values[index]
    
    def reset(self):
        """重置所有指标"""
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
            self._gauges.clear()


# 全局指标收集器实例
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器"""
    return _metrics_collector


def record_request_metrics(endpoint: str, method: str, status_code: int, duration: float):
    """记录请求指标"""
    collector = get_metrics_collector()
    collector.increment("http_requests_total", labels={"endpoint": endpoint, "method": method, "status": str(status_code)})
    collector.record_duration("http_request_duration_seconds", duration, labels={"endpoint": endpoint, "method": method})
    
    if status_code >= 500:
        collector.increment("http_errors_total", labels={"endpoint": endpoint, "method": method})


def record_agent_metrics(execution_time: float, tool_calls: int, success: bool):
    """记录 Agent 执行指标"""
    collector = get_metrics_collector()
    collector.record_duration("agent_execution_duration_seconds", execution_time)
    collector.increment("agent_tool_calls_total", value=tool_calls)
    
    if success:
        collector.increment("agent_executions_total", labels={"status": "success"})
    else:
        collector.increment("agent_executions_total", labels={"status": "error"})


def record_tool_metrics(tool_name: str, execution_time: float, success: bool):
    """记录工具执行指标"""
    collector = get_metrics_collector()
    collector.record_duration(f"tool_{tool_name}_duration_seconds", execution_time)
    
    if success:
        collector.increment(f"tool_{tool_name}_calls_total", labels={"status": "success"})
    else:
        collector.increment(f"tool_{tool_name}_calls_total", labels={"status": "error"})

