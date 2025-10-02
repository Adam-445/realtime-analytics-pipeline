import asyncio

from performance.core.config import TestConfig
from performance.reporting.console import print_summary
from performance.scenarios.throughput import ThroughputScenario


async def run_single_test(target_rps: int, duration: int = 60):
    config = TestConfig(
        target_rps=target_rps,
        duration_seconds=duration,
        max_concurrent_connections=min(target_rps, 1000),
        connection_pool_size=min(target_rps // 2, 500),
    )
    scenario = ThroughputScenario(config)
    try:
        await scenario.setup()
        metrics = await scenario.run()
        print_summary(metrics, config)
        return metrics
    finally:
        await scenario.cleanup()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        target_rps = int(sys.argv[1])
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        print(f"Running single test: {target_rps} RPS for {duration}s")
        asyncio.run(run_single_test(target_rps, duration))
    else:

        async def run_all():
            test_scenarios = [(500, 30), (1000, 60)]
            for rps, dur in test_scenarios:
                print("\n" + "=" * 60)
                print(f"TESTING: {rps} RPS for {dur}s")
                print("=" * 60)
                await run_single_test(rps, dur)
                await asyncio.sleep(5)

        asyncio.run(run_all())
