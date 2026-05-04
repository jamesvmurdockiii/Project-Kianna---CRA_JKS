# Tier 4.25A Blockers

## [INFO] ITCM

**Description:** ITCM footprint measured by 4.24b: text=13,608 bytes / 32,768 bytes = 41.5%. Comfortable headroom for inter-core messaging code.

**Mitigation:** Re-measure if adding significant new code (e.g., inter-core SDP handlers, DMA logic)

## [INFO] SDRAM

**Description:** SDRAM usage not measured — schedule arrays could move to SDRAM to free DTCM

**Mitigation:** DMA schedule from SDRAM to DTCM on demand; measure bandwidth vs latency tradeoff

## [WARNING] latency

**Description:** Inter-core packet latency is 200-1000ns CPU overhead + routing delay. At 1ms timestep, this is 0.02-0.1% of tick.

**Mitigation:** Batch messages, use DMA bursts, or relax timestep for multi-core splits

## [BLOCKING] architecture

**Description:** Dynamic population creation mid-run is NOT supported by current runtime

**Mitigation:** Static pool allocation only. All slots/horizons predeclared at compile time.

