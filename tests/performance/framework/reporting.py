import csv
import json
import os
import socket
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import threading


@dataclass
class RunMeta:
    started_at: float
    finished_at: Optional[float] = None
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    host: str = field(default_factory=lambda: socket.gethostname())
    scenario: str = os.environ.get("PERF_SCENARIO", "all")
    rates: Optional[str] = os.environ.get("PERF_RATES")
    duration: Optional[str] = os.environ.get("PERF_DURATION")
    warmup: Optional[str] = os.environ.get("PERF_WARMUP")
    latency_max: Optional[str] = os.environ.get("PERF_LATENCY_MAX")
    rate_factor: Optional[str] = os.environ.get("PERF_RATE_FACTOR")
    success_min: Optional[str] = os.environ.get("PERF_SUCCESS_MIN")


class PerfReporter:
    """Collects performance results and emits artifacts (CSV/JSON/Markdown).

    Artifacts:
      - perf_summary.json: run meta + detailed results
      - throughput_results.csv: enriched per-rate rows
      - perf_summary.md: human-friendly table for quick viewing
    """

    def __init__(self, out_dir: str):
        self.out_dir = out_dir
        os.makedirs(self.out_dir, exist_ok=True)
        # Use a run_id to make artifacts traceable and keep history
        self.run_id = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        self.meta = RunMeta(
            started_at=time.time(),
            git_commit=os.environ.get("GIT_COMMIT"),
            git_branch=os.environ.get("GIT_BRANCH"),
        )
        self.results: Dict[str, Any] = {
            "throughput": [],
            "latency": [],
            "latency_distributions": [],
        }
        # Optional: system metrics sampling (psutil if available)
        self._sys_metrics_thread: Optional[threading.Thread] = None
        self._sys_metrics_stop = threading.Event()
        self._sys_metrics_samples: List[Dict[str, float]] = []
        # Optional: baseline comparison
        self._baseline: Optional[Dict[str, Any]] = None

    def add_throughput(
        self,
        *,
        target_rate: int,
        actual_send_rate: float,
        sent: int,
        processed: int,
        success_rate: float,
        thresholds: Dict[str, Any],
        passed: bool,
        variant: Optional[str] = None,
    ):
        # Derived metrics
        rate_gap = target_rate - actual_send_rate
        row = {
            "target_rate": target_rate,
            "actual_send_rate": actual_send_rate,
            "sent": sent,
            "processed": processed,
            "success_rate": success_rate,
            "rate_gap": rate_gap,
            "thresholds": thresholds,
            "passed": passed,
            "variant": variant or os.environ.get("PERF_VARIANT", "single"),
        }
        self.results["throughput"].append(row)
        self._append_csv(
            "throughput_results.csv",
            row,
            [
                "target_rate",
                "actual_send_rate",
                "sent",
                "processed",
                "success_rate",
                "rate_gap",
                "variant",
                "passed",
                "thresholds",
            ],
        )

    def add_latency(
        self,
        *,
        e2e_latency_seconds: float,
        thresholds: Dict[str, Any],
        passed: bool,
    ):
        row = {
            "e2e_latency_seconds": e2e_latency_seconds,
            "thresholds": thresholds,
            "passed": passed,
        }
        self.results["latency"].append(row)

    def add_latency_distribution(
        self,
        *,
        name: str,
        latencies: List[float],
        thresholds: Optional[Dict[str, Any]] = None,
        passed: Optional[bool] = None,
    ) -> None:
        """Add a latency distribution summary for reporting."""
        if not latencies:
            summary = {"name": name, "count": 0}
        else:
            vals = sorted(latencies)
            n = len(vals)
            
            def pct(p: float) -> float:
                if n == 1:
                    return float(vals[0])
                k = int(round((p / 100.0) * (n - 1)))
                k = max(0, min(n - 1, k))
                return float(vals[k])
            summary = {
                "name": name,
                "count": n,
                "min": float(vals[0]),
                "max": float(vals[-1]),
                "avg": float(sum(vals) / n),
                "p50": pct(50.0),
                "p95": pct(95.0),
                "p99": pct(99.0),
            }
        if thresholds is not None:
            summary["thresholds"] = thresholds
        if passed is not None:
            summary["passed"] = passed
        self.results["latency_distributions"].append(summary)

    def _append_csv(self, name: str, row: Dict[str, Any], headers: List[str]):
        path = os.path.join(self.out_dir, name)
        file_exists = os.path.exists(path)
        with open(path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            if not file_exists:
                writer.writeheader()
            # stringify thresholds for readability
            r = dict(row)
            if isinstance(r.get("thresholds"), dict):
                r["thresholds"] = json.dumps(r["thresholds"])  # compact
            writer.writerow({k: r.get(k) for k in headers})

    # ---- System metrics sampling (optional) ----
    def start_system_metrics(self, interval: float = 1.0):
        """Start sampling CPU and memory if psutil is available."""
        if self._sys_metrics_thread is not None:
            return
        try:
            import psutil  # type: ignore
        except Exception:
            return

        def _sampler():
            proc = psutil.Process()
            # Prime cpu_percent measurement
            proc.cpu_percent(interval=None)
            while not self._sys_metrics_stop.is_set():
                try:
                    sample = {
                        "ts": time.time(),
                        "cpu_percent": proc.cpu_percent(interval=None),
                        "rss_bytes": float(proc.memory_info().rss),
                        "sys_cpu_percent": psutil.cpu_percent(interval=None),
                        "sys_mem_percent": psutil.virtual_memory().percent,
                    }
                    self._sys_metrics_samples.append(sample)
                except Exception:
                    pass
                # Wait interval with stop support
                self._sys_metrics_stop.wait(timeout=interval)

        self._sys_metrics_stop.clear()
        self._sys_metrics_thread = threading.Thread(
            target=_sampler, name="perf-sys-metrics", daemon=True
        )
        self._sys_metrics_thread.start()

    def stop_system_metrics(self):
        if self._sys_metrics_thread is None:
            return
        self._sys_metrics_stop.set()
        try:
            self._sys_metrics_thread.join(timeout=2.0)
        except Exception:
            pass
        self._sys_metrics_thread = None

    def _summarize_system_metrics(self) -> Optional[Dict[str, float]]:
        if not self._sys_metrics_samples:
            return None

        def _agg(key: str) -> Tuple[float, float, float]:
            vals = [s[key] for s in self._sys_metrics_samples if key in s]
            if not vals:
                return (0.0, 0.0, 0.0)
            return (sum(vals) / len(vals), max(vals), min(vals))

        cpu_avg, cpu_max, _ = _agg("cpu_percent")
        sys_cpu_avg, sys_cpu_max, _ = _agg("sys_cpu_percent")
        mem_avg, mem_max, _ = _agg("rss_bytes")
        sys_mem_avg, sys_mem_max, _ = _agg("sys_mem_percent")
        return {
            "proc_cpu_avg": cpu_avg,
            "proc_cpu_max": cpu_max,
            "proc_rss_avg_bytes": mem_avg,
            "proc_rss_max_bytes": mem_max,
            "sys_cpu_avg": sys_cpu_avg,
            "sys_cpu_max": sys_cpu_max,
            "sys_mem_avg": sys_mem_avg,
            "sys_mem_max": sys_mem_max,
        }

    # ---- Baseline comparison (optional) ----
    def load_baseline(self, path: str):
        try:
            with open(path, "r") as f:
                self._baseline = json.load(f)
        except Exception:
            self._baseline = None

    def _render_comparison_markdown(self) -> Optional[str]:
        if not self._baseline:
            return None
        lines: List[str] = []
        lines.append("\n## Comparison vs Baseline\n\n")
        try:
            base_tp = self._baseline.get("results", {}).get("throughput", [])
            cur_tp = self.results.get("throughput", [])
            if base_tp and cur_tp:
                # Compare averages
                def avg(lst, key):
                    vals = [float(x.get(key, 0.0)) for x in lst]
                    return sum(vals) / len(vals) if vals else 0.0

                base_send = avg(base_tp, "actual_send_rate")
                cur_send = avg(cur_tp, "actual_send_rate")
                base_succ = avg(base_tp, "success_rate")
                cur_succ = avg(cur_tp, "success_rate")
                delta_send = cur_send - base_send
                lines.append(
                    f"- Send rate: {cur_send:.2f} vs {base_send:.2f} "
                    f"(Δ {delta_send:+.2f})\n"
                )
                delta_succ_pp = (cur_succ - base_succ) * 100
                lines.append(
                    f"- Success rate: {cur_succ:.2%} vs {base_succ:.2%} "
                    f"(Δ {delta_succ_pp:+.2f} pp)\n"
                )
        except Exception:
            return None
        return "".join(lines) if lines else None

    def flush(self):
        self.meta.finished_at = time.time()
        payload = {
            "run_id": self.run_id,
            "meta": asdict(self.meta),
            "results": self.results,
        }
        # Attach optional system metrics summary
        sys_summary = self._summarize_system_metrics()
        if sys_summary:
            payload["system_metrics"] = sys_summary
        # JSON summary (latest and timestamped)
        self._write_file("perf_summary.json", json.dumps(payload, indent=2))
        self._write_file(
            f"perf_summary_{self.run_id}.json", json.dumps(payload, indent=2)
        )
        # Markdown summary (latest and timestamped)
        md = self._render_markdown()
        # Append baseline comparison if available
        comp = None
        baseline_path = os.environ.get("PERF_BASELINE_FILE")
        if baseline_path:
            self.load_baseline(baseline_path)
            comp = self._render_comparison_markdown()
            if comp:
                md = md + comp
        self._write_file("perf_summary.md", md)
        self._write_file(f"perf_summary_{self.run_id}.md", md)
        # Append run to index.csv
        self._append_csv(
            "runs_index.csv",
            {
                "run_id": self.run_id,
                "git_branch": self.meta.git_branch,
                "git_commit": self.meta.git_commit,
                "scenario": self.meta.scenario,
                "rates": self.meta.rates,
                "duration": self.meta.duration,
                "warmup": self.meta.warmup,
                "started_at": self.meta.started_at,
                "finished_at": self.meta.finished_at,
            },
            [
                "run_id",
                "git_branch",
                "git_commit",
                "scenario",
                "rates",
                "duration",
                "warmup",
                "started_at",
                "finished_at",
            ],
        )
        # Console hint for users
        try:
            print({"perf_results_dir": self.out_dir, "run_id": self.run_id})
        except Exception:
            pass

    def _write_file(self, name: str, content: str):
        with open(os.path.join(self.out_dir, name), "w") as f:
            f.write(content)

    def _render_markdown(self) -> str:
        lines: List[str] = []
        lines.append("# Performance Summary\n")
        lines.append(f"- Run ID: {self.run_id}  \n")
        lines.append(f"- Branch: {self.meta.git_branch or '-'}  \n")
        lines.append(f"- Commit: {self.meta.git_commit or '-'}  \n")
        lines.append(f"- Scenario: {self.meta.scenario}  \n")
        lines.append(f"- Rates: {self.meta.rates or '-'}  \n")
        lines.append(f"- Duration: {self.meta.duration or '-'} s  \n")
        lines.append(f"- Warmup: {self.meta.warmup or '-'} s  \n")
        lines.append("\n## Throughput\n\n")
        if self.results["throughput"]:
            lines.append(
                "| target | variant | actual_send | sent | processed | "
                "success | pass |\n"
            )
            lines.append("|---:|:--|---:|---:|---:|---:|:---:|\n")
            for r in self.results["throughput"]:
                row_line = (
                    "| {target} | {variant} | {actual:.2f} | {sent} | {processed} | "
                    "{success:.2%} | {passed} |\n"
                ).format(
                    target=r["target_rate"],
                    variant=r.get("variant") or "-",
                    actual=r["actual_send_rate"],
                    sent=r["sent"],
                    processed=r["processed"],
                    success=r["success_rate"],
                    passed=("✅" if r["passed"] else "❌"),
                )
                lines.append(row_line)
        else:
            lines.append("(no throughput results)\n")
        lines.append("\n## Latency\n\n")
        if self.results["latency"]:
            for r in self.results["latency"]:
                lines.append(
                    "- e2e_latency: {lat:.3f}s {ok}\n".format(
                        lat=r["e2e_latency_seconds"],
                        ok=("✅" if r["passed"] else "❌"),
                    )
                )
        else:
            lines.append("(no latency result)\n")
        # Latency distributions (optional)
        if self.results.get("latency_distributions"):
            lines.append("\n## Latency Distributions\n\n")
            lines.append("| name | count | p50 | p95 | p99 | avg | min | max |\n")
            lines.append("|:--|---:|---:|---:|---:|---:|---:|---:|\n")
            for d in self.results.get("latency_distributions", []):
                if not d:
                    continue
                try:
                    lines.append(
                        "| {name} | {count} | {p50:.3f}s | {p95:.3f}s | {p99:.3f}s | "
                        "{avg:.3f}s | {min:.3f}s | {max:.3f}s |\n".format(**d)
                    )
                except Exception:
                    lines.append(f"- {d}\n")
        # Optional system metrics
        sys_summary = self._summarize_system_metrics()
        if sys_summary:
            lines.append("\n## System Metrics (test process)\n\n")
            cpu_avg = sys_summary['proc_cpu_avg']
            cpu_max = sys_summary['proc_cpu_max']
            rss_avg = int(sys_summary['proc_rss_avg_bytes'])
            rss_max = int(sys_summary['proc_rss_max_bytes'])
            sys_cpu_avg = sys_summary['sys_cpu_avg']
            sys_cpu_max = sys_summary['sys_cpu_max']
            sys_mem_avg = sys_summary['sys_mem_avg']
            sys_mem_max = sys_summary['sys_mem_max']
            lines.append(f"- CPU avg/max: {cpu_avg:.1f}% / {cpu_max:.1f}%\n")
            lines.append(f"- RSS avg/max: {rss_avg} / {rss_max} bytes\n")
            lines.append(
                f"- System CPU avg/max: {sys_cpu_avg:.1f}% / {sys_cpu_max:.1f}%\n"
            )
            lines.append(
                f"- System Mem avg/max: {sys_mem_avg:.1f}% / {sys_mem_max:.1f}%\n"
            )
        return "".join(lines)
