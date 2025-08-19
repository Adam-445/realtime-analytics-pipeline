from typing import Any, Optional

import requests


class Prometheus:
    def __init__(self, base_url: str, timeout: float = 3.0, retries: int = 2):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = max(0, int(retries))

    def _get(self, path: str, params: dict) -> Any:
        last_err: Optional[Exception] = None
        for _ in range(self.retries + 1):
            try:
                resp = requests.get(
                    f"{self.base_url}{path}", params=params, timeout=self.timeout
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("status") != "success":
                    raise RuntimeError(f"Prometheus query failed: {data}")
                return data.get("data", {}).get("result", [])
            except Exception as e:
                last_err = e
        # If all retries failed, re-raise the last error
        if last_err:
            raise last_err
        return []

    def query(self, promql: str) -> Any:
        return self._get("/api/v1/query", {"query": promql})

    def query_range(self, promql: str, start: float, end: float, step: float) -> Any:
        params = {"query": promql, "start": start, "end": end, "step": step}
        return self._get("/api/v1/query_range", params)

    def query_value(self, promql: str) -> float | None:
        result = self.query(promql)
        if not result:
            return None
        # Assume scalar/vector with single sample
        try:
            value = float(result[0]["value"][1])
            return value
        except Exception:
            return None
