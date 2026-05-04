# Tier 4.27g — SDP-vs-MCPL Protocol Comparison

**Generated:** 2026-05-03T03:11:25.363560+00:00
**Status:** PASS
**Claim boundary:** Source-code-based protocol analysis only. NOT hardware timing measurements. NOT router-table hardware validation. NOT multi-chip scaling evidence.

## 1. Payload Overhead per Lookup Round-Trip

| Protocol | Request | Reply | Round-Trip |
|----------|---------|-------|------------|
| SDP      | 26 bytes | 28 bytes | 54 bytes |
| MCPL     | 8 bytes | 8 bytes | 16 bytes |

**Reduction:** MCPL uses 29% of SDP bytes per round-trip.

## 2. Per-Event Message Counts (48-Event Reference)

- Lookup types per event: 3
- Inter-core messages per event: 6
- Total lookup messages (48 events): 288
- SDP total bytes (~48 events): ~8064 bytes
- MCPL total bytes (~48 events): ~2304 bytes

## 3. Router Table Entries

- SDP: **0** entries (monitor processor routes)
- MCPL: **4** entries (hardware router)

MCPL entry breakdown:

- **context_core:** match REQUEST/CONTEXT keys -> route to context core
- **route_core:** match REQUEST/ROUTE keys -> route to route core
- **memory_core:** match REQUEST/MEMORY keys -> route to memory core
- **learning_core:** match REPLY/* keys (mask 0xFFFF0000) -> route to learning core

- Learning core mask: `0xFFFF0000 (ignores lookup_type and seq_id)`

## 4. Failure Modes

### SDP
- Monitor processor SDP queue overflow (core sends faster than monitor routes)
- Destination core mailbox full (32-entry limit per core)
- Monitor processor crash or reset during routing
- **Drop behavior:** Learning core times out; no automatic retry; request counted as timeout
- **Scaling risk:** Monitor processor is single bottleneck; risk increases with core count

### MCPL
- Router table miss (no matching entry for key)
- Router congestion (too many multicast packets in flight)
- Multicast key collision with another application
- **Drop behavior:** Learning core times out; same timeout counter as SDP
- **Scaling risk:** Hardware router is parallel and chip-wide; scales better than monitor processor

## 5. Latency Paths

### SDP
- **Path:** Source core -> monitor processor SDP queue -> monitor parses header -> monitor writes to dest core mailbox -> dest core CPU reads mailbox
- **Bottleneck:** Monitor processor CPU and mailbox delivery loop
- **Estimate:** ~5-20 us per hop (monitor-dependent)
- **Notes:** Monitor processor is shared across all 18 cores; contention increases latency

### MCPL
- **Path:** Source core -> hardware router key match -> router forwards to target core(s) -> target core DMA receives packet -> Spin1API callback fires
- **Bottleneck:** Router table lookup (hardware, parallel)
- **Estimate:** ~0.5-2 us per hop (hardware router)
- **Notes:** No monitor involvement; router handles all keys in parallel; latency is deterministic

## 6. Implementation Risk Assessment

- **SDP maturity:** PROVEN — 4.27a hardware pass on board 10.11.194.65 with 144/144 lookup requests/replies, zero timeouts
- **MCPL maturity:** COMPILE-FEASIBLE + WIRED — 4.27d/f pass locally; all four profiles build; callback wired; router init defined
- **MCPL hardware uncertainty:** Router table load behavior not yet validated on actual SpiNNaker chip
- **SDP risk:** LOW for 4-core; HIGH for scaling beyond 4 cores (monitor bottleneck)
- **MCPL risk:** LOW for intra-chip; MEDIUM for inter-chip (untested)

### Recommendation

Make MCPL the default inter-core lookup data plane for Tier 4.28+; keep SDP code path as fallback until MCPL hardware smoke passes

## Pass Criteria

- ✓ runner revision current
- ✓ SDP request path exists in source
- ✓ SDP reply path exists in source
- ✓ MCPL request path exists in source
- ✓ MCPL reply path exists in source
- ✓ MCPL callback wired in main.c
- ✓ MCPL init wired in main.c
- ✓ MCPL round-trip smaller than SDP
- ✓ router entry count documented
- ✓ failure modes documented
- ✓ latency paths documented
- ✓ risk recommendation explicit
