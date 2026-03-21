# OpenClaw concurrency audit

Historical snapshot imported from the legacy in-tree OpenClaw runtime during decommission prep.

Date: 2026-03-09
Scope: local runtime audit for OpenClaw on this machine

## Executive summary

Keeping OpenClaw at `1` concurrent run currently makes operational sense, but not because of CPU shortage.

The observed bottlenecks are:
- long-running LLM and cron tasks;
- memory pressure inside systemd limits;
- recurring stuck/restart behavior in the Telegram channel health monitor.

Storage is not a limiting factor at the moment.

## Current configuration

Current runtime config in `openclaw.json`:
- `agents.defaults.maxConcurrent = 1`
- `agents.defaults.subagents.maxConcurrent = 1`
- `agents.defaults.subagents.runTimeoutSeconds = 600`

Important interpretation:
- this is not "1 OS process per CPU core";
- in OpenClaw, `maxConcurrent` limits parallel agent runs inside one gateway runtime;
- increasing it raises simultaneous contexts, requests, buffers, and memory footprint.

OpenClaw upstream defaults observed in installed package:
- agent concurrency default: `4`
- subagent concurrency default: `8`

This means the current `1` is an explicit conservative override, not a factory default.

## Host capacity

Host snapshot during audit:
- CPU cores: `8`
- load average: about `0.94 / 0.83 / 0.76`
- CPU idle in sampling: about `76-98%`
- OpenClaw process CPU: about `3.3%`

Conclusion on CPU:
- CPU is not the current bottleneck;
- there is enough headroom to increase parallelism from a pure CPU perspective.

## Memory and limits

OpenClaw systemd limits:
- `MemoryHigh=700M`
- `MemoryMax=900M`
- `MemorySwapMax=1200M`

Observed service memory:
- `MemoryCurrent=441M`
- `MemoryPeak=734M`
- `MemorySwapCurrent=168M`
- `MemorySwapPeak=429M`

Interpretation:
- the service already crossed the soft pressure zone and reached above `MemoryHigh`;
- the process is actively using swap;
- raising concurrency will likely increase RAM and swap pressure before CPU becomes a problem.

Conclusion on memory:
- RAM, not CPU, is the more relevant constraint for concurrency growth in the current setup.

## Storage

Observed storage:
- `/` free space: about `23G`
- total OpenClaw directory: about `1.5G`
- `node_modules`: about `1.4G`
- runtime `state`: about `93M`
- `workspace`: about `2.4M`

Interpretation:
- disk usage is dominated by dependencies, not live runtime growth;
- runtime state size is currently modest;
- storage does not justify keeping concurrency at `1`.

## Runtime symptoms in logs

Observed recurring symptoms:
- repeated `health-monitor: restarting (reason: stuck)` for Telegram;
- repeated `embedded run timeout` around `600000ms`;
- cron wait growth up to `554584ms`;
- `queueAhead` observed up to `5`.

Interpretation:
- the system is not mostly waiting for CPU;
- it is getting blocked by slow or hanging external runs and long queue residence time;
- extra concurrency can improve throughput in some cases, but it also multiplies in-flight contexts and memory use.

## Historical signal

Config backups indicate:
- one older backup had `maxConcurrent = 2`;
- current config and most recent backups are at `1`.

Interpretation:
- this looks like a deliberate move toward a more conservative runtime posture;
- the current limit is likely chosen for stability, not because the host lacks cores.

## Recommendation

Current recommendation:
- keep `agents.defaults.maxConcurrent = 1` for now if the main goal is stability;
- do not jump directly to `3` under the current memory limits.

If concurrency testing is desired:
- first test `agents.defaults.maxConcurrent = 2`;
- keep `subagents.maxConcurrent = 1` initially;
- watch `MemoryPeak`, `MemorySwapCurrent`, `MemorySwapPeak`, timeout frequency, and stuck restarts.

What would justify a move to `3`:
- either higher memory limits for the service with acceptable swap behavior;
- or evidence from a controlled `2`-concurrency trial that timeouts and stuck conditions do not worsen.

## Final conclusion

Answer to the main question:
- yes, there is CPU headroom for more concurrency;
- no, the decision should not be based on CPU alone;
- the stronger reason to keep OpenClaw at `1` right now is memory pressure plus instability under long-running tasks;
- ROM/disk is not a meaningful blocker in the current state.
