# Sbuffer Specification Document

> This document describes the specification of the `Sbuffer` chip verification target. Keep the technical language precise, well-organized, and easy to reuse for verification. If an item does not exist, explicitly write "None" or "TBD"; do not delete the section.

## Introduction

- **Design Background**: The Sbuffer (Store Buffer) is a module in the XiangShan CPU memory subsystem. It sits between the store queue (SQ) and the L1 data cache (DCache). The store queue sends committed store requests to the Sbuffer, which buffers them and later evicts cache-line-wide write requests to the DCache. Load pipelines query the Sbuffer for store-to-load forwarding.
- **Design Goals**: (1) Accept up to `EnbufferWidth` store requests per cycle, inserting new entries or merging into existing entries whose physical address matches. (2) Evict buffered entries to the DCache via a priority-based selection scheme. (3) Forward the most recent byte-level store data to load pipeline queries when the virtual address matches an active entry. (4) Provide difftest trace events for functional verification against a reference model.

## Terms and Abbreviations in Chisel Code

| Abbreviation | Full Term | Description |
| ---- | ---- | ---- |
| SQ | Store Queue | Upstream unit that sends committed store requests to the Sbuffer |
| DCache | L1 Data Cache | Downstream unit that receives cache-line write requests from the Sbuffer |
| PLRU | Pseudo Least Recently Used | Replacement policy for selecting eviction candidates among dcache-req-candidate entries |
| cohCount | Coherence Counter | Per-entry counter that increments each cycle; eviction is triggered when the top bit is set |
| missqReplayCount | Miss-Queue Replay Counter | Per-entry counter that increments after a replay response; timeout enables retry |
| vtag | Virtual Address Tag | High-order bits of the virtual address used for load-forward matching |
| ptag | Physical Address Tag | High-order bits of the physical address used for eviction addressing and merge/insert decisions |
| CAM | Content Addressable Memory | Tag-matching logic used in forward and merge lookups |
| FSM | Finite State Machine | The top-level `sbuffer_state` controller (x_idle/x_replace/x_drain_all/x_drain_sbuffer) |
| PseudoLRU | Pseudo Least Recently Used | Tree-based approximate LRU structure for replacement |
| Difftest | Differential Testing | Verification framework comparing RTL events against a reference model (NEMU) |

## Chisel Source Files

The Sbuffer module is extracted as a single file.

File list:
- `fm_agent/extracted_functions/Sbuffer-scala/Sbuffer.scala`: Top-level Sbuffer module containing the enqueue logic, eviction pipeline, load-forwarding CAM, difftest instrumentation, and the main FSM.

## Top-Level Interface Overview

- **Module Name**: `Sbuffer`
- **Port List**:

| Signal Name | Direction | Width/Type | Reset Value | Description |
| ------ | ---- | -------- | ------ | ---- |
| clock | input | Clock | N/A | Clock signal |
| reset | input | Reset | N/A | Reset signal |
| hartId | input | UInt(hartIdLen.W) | N/A | Hart ID for difftest event tagging |
| in[i] | input | Decoupled(DCacheWordReqWithVaddrAndPfFlag), x EnbufferWidth | N/A | Store-queue requests: addr, vaddr, data, mask, wline, vecValid, prefetch |
| dcache.req | output | Decoupled(DCacheWriteReq) | N/A | DCache write request: cmd=M_XWR, addr, vaddr, data, mask, id |
| dcache.hit_resps[j] | input | Valid(DCacheResp), x N | N/A | DCache hit responses: id, replay, miss |
| dcache.replay_resp | input | Valid(DCacheResp) | N/A | DCache replay response: id, replay=true |
| dcache.main_pipe_hit_resp | input | Valid(DCacheResp) | N/A | Main-pipeline hit response |
| forward[k] | input | LoadForwardQueryIO, x LoadPipelineWidth | N/A | Load-forward queries: vaddr, paddr, valid |
| forward[k].dataInvalid | output | Bool | false | Always deasserted (Sbuffer data always ready) |
| forward[k].matchInvalid | output | Bool | N/A | Asserted when vtag match and ptag match disagree |
| forward[k].forwardMask | output | Vec(VDataBytes, Bool) | all-false | Byte-level forwarding mask |
| forward[k].forwardData | output | Vec(VDataBytes, UInt(8.W)) | DontCare | Byte-level forwarding data |
| forward[k].forwardMaskFast | output | Vec(VDataBytes, Bool) | N/A | Fast (same-cycle) forwarding mask |
| sqempty | input | Bool | N/A | Store queue empty indication |
| sbempty | output | Bool | true after reset | Sbuffer and store queue both empty |
| flush.valid | input | Bool | N/A | Flush trigger from flush controller |
| flush.empty | output | Bool | N/A | Sbuffer and store queue both empty (qualified) |
| csrCtrl | input | CustomCSRCtrlIO | N/A | CSR control for threshold configuration |
| store_prefetch[m] | output | Decoupled(StorePrefetchReq), x StorePipelineWidth | N/A | Store prefetch requests to DCache |
| memSetPattenDetected | input | Bool | N/A | Memory-set pattern detected signal |
| force_write | input | Bool | N/A | Lowers eviction threshold when asserted |
| diffStore | input | DiffStoreIO | DontCare | Differentiated store info for difftest generation |

- **Clock and Reset Requirements**: Single implicit clock domain. All registers are synchronous to this single clock. Synchronous reset. After reset all per-entry state is invalid (`state_valid` = false), all counters are zero, and `sbuffer_state` is `x_idle`. The `sbempty` output is asserted.
- **External Dependencies**: (1) The upstream store queue must present valid request data only when `io.in(i).valid` is asserted; the Sbuffer drives `ready` based on available capacity. (2) The DCache must accept write requests via `dcache.req` with standard Decoupled handshake; the Sbuffer blocks eviction when the DCache backpressures. (3) The DCache must return either a hit response or a replay response for every accepted write request. (4) The flush controller must hold `flush.valid` until the Sbuffer drains; the Sbuffer asserts `flush.empty` when both Sbuffer and store queue are empty.

## Functional Description

### Enqueue / Store Acceptance

<FG-ENQUEUE>

- **Overview**: The Sbuffer accepts up to `EnbufferWidth` store requests per cycle from the store queue via `io.in`. Each request carries a physical address, virtual address, byte-level write data, and a write mask. On acceptance, the Sbuffer either allocates a new entry (insert) or combines the write into an existing entry whose physical tag matches (merge). Accepted requests flow through a 3-stage pipeline (sbuffer_in_s0/s1/s2) before data and mask are committed to `SbufferData`.
- **Boundaries and Exceptions**: (1) When `sbuffer_state == x_drain_sbuffer`, `io.in(i).ready` is deasserted (no new inserts allowed). (2) If a merge candidate is found but the incoming vtag differs from the stored vtag, `merge_need_uarch_drain` is asserted, triggering an architectural drain. (3) If both input channels target the same physical address (`sameTag`), the second channel uses the same insert slot as the first; merged entries have no constraint on even/odd slot assignment. (4) A merge that would set more than one bit in `mergeMask` for a valid input fires an assertion. (5) Backpressure is signaled via `ready` deassertion when all even/odd slots are exhausted or the Sbuffer is in drain state.
- **Performance and Constraints**: Up to `EnbufferWidth` requests accepted per cycle. The total number of buffered entries is bounded by `StoreBufferSize`. Insert and merge decisions are made combinatorially in the fire cycle.

#### Insert — New Entry Allocation

<FC-INSERT>

When no active entry matches the incoming request's physical tag, the Sbuffer allocates a new entry at the first available even-indexed or odd-indexed invalid slot. The entry is initialized with the request's ptag, vtag, a zeroed `cohCount`, and `w_sameblock_inflight` set if any entry for the same cache block is currently inflight. Data and mask are written to `SbufferData` at the word offset derived from the physical address.

**Check points:**
- <CK-INSERT-VALID> After an insert fire, the allocated entry transitions from invalid to valid (isActive() = true) and retains the correct ptag, vtag, and byte-level data/mask.
- <CK-INSERT-SAMEBLOCK-INFLIGHT> If another entry targeting the same cache block is inflight when the insert occurs, `w_sameblock_inflight` is set for the newly allocated entry.
- <CK-INSERT-FULL> When all `StoreBufferSize` entries are active and no merge is possible, `ready` is deasserted for all input channels.
- <CK-INSERT-DRAIN-BLOCKED> When `sbuffer_state == x_drain_sbuffer`, all `ready` signals are deasserted regardless of available capacity.

#### Merge — Existing Entry Update

<FC-MERGE>

When an incoming request's physical tag matches an active entry, the Sbuffer merges the request into that entry: the per-entry `cohCount` is reset to zero, the `SbufferData` entry is updated at the word offset with the new data and mask, and the entry remains in active state.

**Check points:**
- <CK-MERGE-DATA> After a merge fire, the targeted entry's data at the written word offset reflects the merged data; bytes outside the write mask are unchanged.
- <CK-MERGE-COH-RESET> The merged entry's `cohCount` is reset to zero after the merge.
- <CK-MERGE-VTAG-MISMATCH> When the incoming vtag differs from the stored vtag, `merge_need_uarch_drain` is asserted and the Sbuffer subsequently transitions to `x_drain_sbuffer`.
- <CK-MERGE-DUAL-INPUT> When both input channels fire in the same cycle and the second targets the same ptag as the first, the merge count is exactly 2.

#### Two-Wide Enqueue with Same-Tag Coalescing

<FC-DUAL-ENQUEUE>

When `EnbufferWidth >= 2` and both `io.in(0)` and `io.in(1)` fire in the same cycle, the Sbuffer processes both requests. If both requests target the same physical tag (`sameTag`), the second request uses the same insert slot index as the first, and the two requests are coalesced into a single Sbuffer entry.

**Check points:**
- <CK-DUAL-INDEPENDENT> When the two requests have different ptags and both fire, each is allocated (or merged into) a distinct Sbuffer entry.
- <CK-DUAL-SAMETAG-MERGE> When both requests have the same ptag and the first request's ptag matches an active entry, both requests merge into the same entry.
- <CK-DUAL-SAMETAG-INSERT> When both requests have the same ptag but the ptag does not match any active entry, a single new entry is allocated and both word offsets are updated.

### Eviction / DCache Write

<FG-EVICTION>

- **Overview**: The Sbuffer selects one entry per cycle for eviction and sends a cache-line-wide write request to the DCache. The selection priority (highest to lowest) is: miss-queue replay timeout, flush drain, coherence timeout, PLRU replacement. The eviction pipeline has two stages (sbuffer_out_s0/s1): stage 0 reads entry data and sets the entry state to inflight; stage 1 sends the DCache write request. Write responses from the DCache complete the entry lifecycle: a hit response invalidates the entry, while a replay response sets `w_timeout` and waits for the replay timeout counter before retry.
- **Boundaries and Exceptions**: (1) An entry is not selected if `noSameBlockInflight` is false (another entry for the same cache block is inflight). (2) A pending write to `SbufferData` (write-in-flight hazard) blocks the DCache request issue via `blockDcacheWrite`. (3) A flush asserted during eviction transitions the state machine to `x_drain_all`; the current eviction completes, then all entries are drained. (4) The PLRU replacement policy selects among dcache-request-candidate entries only.
- **Performance and Constraints**: At most one entry evicted per cycle. The sbuffer_out_s1 pipeline can hold at most one request at a time.

#### Eviction Arbitration

<FC-ARBITRATION>

The Sbuffer selects one entry for eviction each cycle using fixed priority: miss-queue replay timeout has highest priority, followed by flush drain, coherence timeout, and PLRU replacement. The selected entry must be a dcache-request candidate (`isDcacheReqCandidate()`) unless the selection is driven by a miss-queue replay timeout.

**Check points:**
- <CK-ARB-PRIORITY> When entries satisfy multiple selection conditions simultaneously, the highest-priority condition (miss-queue replay timeout > drain > coherence timeout > PLRU) determines the selected entry.
- <CK-ARB-SAMEBLOCK-BLOCKED> An entry that is a dcache-request candidate is NOT selected when another entry with the same ptag is inflight (`noSameBlockInflight` returns false).

#### DCache Write Request

<FC-WRITE-REQ>

When sbuffer_out_s1 fires, a write request is presented on `io.dcache.req` with `bits.cmd = M_XWR`, `bits.addr` reconstructed from the evicted entry's ptag, `bits.data` as the full cache-line data, `bits.mask` as the full byte-level mask, and `bits.id` set to the evicted entry index.

**Check points:**
- <CK-WRITE-REQ-FORMAT> On sbuffer_out_s1 fire, `io.dcache.req.bits.cmd` equals M_XWR, `bits.addr` equals `getAddr(evictionPTag)`, and `bits.id` equals the eviction index.
- <CK-WRITE-REQ-DATA> The `bits.data` and `bits.mask` fields contain the full cache-line values from the evicted entry's SbufferData storage.
- <CK-WRITE-REQ-BACKPRESSURE> When `io.dcache.req.ready` is deasserted, the sbuffer_out_s1 pipeline stalls and `io.dcache.req.valid` remains asserted until the DCache accepts the request.

#### DCache Response Handling

<FC-RESPONSE>

The Sbuffer accepts hit responses (`io.dcache.hit_resps`) and replay responses (`io.dcache.replay_resp`). A hit response invalidates the entry (`state_valid = false`, `state_inflight = false`) and triggers a mask flush to SbufferData. A replay response sets `w_timeout = true`, resets `missqReplayCount`, and the entry waits for the timeout counter before retrying.

**Check points:**
- <CK-RESP-HIT-INVALIDATE> On a hit response fire, the entry identified by `resp.bits.id` transitions to invalid: `state_inflight` and `state_valid` both become false.
- <CK-RESP-HIT-MASKFLUSH> On a hit response fire, a mask-flush request targeting the same entry is sent to SbufferData.
- <CK-RESP-REPLAY-TIMEOUT> On a replay response fire, the entry's `w_timeout` is set to true; the entry is not eligible for eviction until the miss-queue replay counter reaches its threshold.
- <CK-RESP-REPLAY-RETRY> After the miss-queue replay timeout expires, the entry becomes a dcache-request candidate again and is re-selected by the arbitration logic.

### Load Data Forwarding

<FG-FORWARD>

- **Overview**: The Sbuffer provides combinational store-to-load forwarding for each of `LoadPipelineWidth` load pipeline queries via `io.forward`. Each query supplies a virtual address and a physical address. The Sbuffer compares the virtual address against all entries' vtags. On a vtag match, the byte-level data and mask for the targeted word offset are forwarded. Active (valid, not inflight) entries take priority over inflight entries. The fast forwarding path bypasses pipeline registers for same-cycle data availability.
- **Boundaries and Exceptions**: (1) If a vtag match and a registered ptag match disagree (`tag_mismatch`), `matchInvalid` is asserted and the Sbuffer triggers `forward_need_uarch_drain`, which causes a transition to `x_drain_sbuffer`. (2) Forwarding data is always considered ready; there is no backpressure on the forward interface. (3) Both the standard (registered) and fast (combinational) forwarding masks are provided.
- **Performance and Constraints**: Forward data is available in the same cycle as the query (combinational read from the register file). Up to `LoadPipelineWidth` queries are serviced simultaneously with independent CAM lookups.

#### Forward Data from Active Entries

<FC-FORWARD-ACTIVE>

When a forward query's vaddr matches an active entry (valid, not inflight), the Sbuffer drives the corresponding byte-level data and mask onto `forward.forwardData` and `forward.forwardMask`. Active entries have higher priority than inflight entries.

**Check points:**
- <CK-FORWARD-ACTIVE-DATA> When exactly one active entry matches the forward vaddr, `forward.forwardData` and `forward.forwardMask` reflect that entry's data and mask at the word offset.
- <CK-FORWARD-ACTIVE-PRIORITY> When both an active entry and an inflight entry match the forward vaddr, the forwarded data comes from the active entry's storage.
- <CK-FORWARD-NO-MATCH> When no entry matches the forward vaddr, all bits of `forward.forwardMask` are false.

#### VTag / PTag Mismatch Detection

<FC-MISMATCH-DETECT>

The Sbuffer compares combinational vtag matching against registered ptag matching for each forward query. When they disagree for an entry that was active or inflight when queried, `matchInvalid` is asserted and an architectural drain is triggered via `forward_need_uarch_drain`.

**Check points:**
- <CK-MISMATCH-ASSERT> When vtag match and registered ptag match disagree for an active or inflight entry, `forward.matchInvalid` is asserted.
- <CK-MISMATCH-DRAIN> After `matchInvalid` is asserted, the Sbuffer transitions to `x_drain_sbuffer` state within a bounded number of cycles.
- <CK-MISMATCH-HARMONIOUS> When vtag match and ptag match agree for all entries, `forward.matchInvalid` remains deasserted.

### Flush and State Management

<FG-FLUSH>

- **Overview**: The Sbuffer implements a 4-state FSM (`sbuffer_state`) that controls entry eviction. The states are `x_idle` (normal operation), `x_replace` (eviction due to threshold or full), `x_drain_all` (flush-triggered full drain), and `x_drain_sbuffer` (micro-architectural drain, blocking new inserts). The FSM transitions are driven by flush requests, eviction conditions, micro-architectural drain triggers (from tag mismatch or merge vtag mismatch), and the buffer-empty condition.
- **Boundaries and Exceptions**: (1) A flush request during `x_drain_sbuffer` upgrades the state to `x_drain_all`. (2) A flush request during `x_replace` upgrades to `x_drain_all`. (3) Micro-architectural drain requests during `x_replace` transition to `x_drain_sbuffer`. (4) The flush interface handshake: the flush controller asserts `flush.valid`; the Sbuffer asserts `flush.empty` when both the Sbuffer and the store queue report empty.
- **Performance and Constraints**: Only one state transition occurs per cycle. The drain-all state waits for the store queue to also be empty before returning to idle.

#### Empty and Flush Status

<FC-EMPTY-STATUS>

The Sbuffer drives `io.sbempty` and `io.flush.empty` to indicate emptiness. `sbempty` is asserted (with a one-cycle glitch filter via `GatedValidRegNext`) when all Sbuffer entries are invalid and all input channels have no valid request. `flush.empty` additionally qualifies with `io.sqempty`.

**Check points:**
- <CK-EMPTY-SBEMPTY> `sbempty` is asserted exactly when all Sbuffer entries are in invalid state and no input channel has a valid request.
- <CK-EMPTY-FLUSH-EMPTY> `flush.empty` is asserted only when both `sbempty` and `sqempty` are true.
- <CK-EMPTY-AFTER-RESET> After reset, both `sbempty` and `flush.empty` are asserted.

### Coherence and Replay Timeout

<FG-TIMEOUT>

- **Overview**: Each active entry maintains a `cohCount` that increments every cycle. When the top bit (`EvictCountBits-1`) of `cohCount` is set, the entry is evicted (coherence timeout). Separately, entries that receive a DCache replay response set `w_timeout` and begin incrementing `missqReplayCount`. When the top bit of `missqReplayCount` is set, the entry becomes eligible for retry.
- **Boundaries and Exceptions**: (1) `cohCount` is reset to zero on insert or merge. (2) `missqReplayCount` is reset on insert and on replay response. (3) Coherence timeout eviction is blocked if a same-block-inflight condition exists.
- **Performance and Constraints**: `cohCount` timeout is approximately `1 << (EvictCountBits-1)` cycles. `missqReplayCount` timeout is `SbufferReplayDelayCycles` (16 cycles default).

#### Coherence Timeout Eviction

<FC-COH-TIMEOUT>

An active entry whose `cohCount` reaches the timeout threshold (top bit set) is selected for eviction via `cohTimeOutMask`, gated by the arbitration priority (below miss-queue replay timeout and drain).

**Check points:**
- <CK-COH-TIMEOUT-THRESHOLD> An active entry is selected for eviction by coherence timeout exactly when `cohCount(i)(EvictCountBits-1)` is asserted.
- <CK-COH-TIMEOUT-RESET> After a merge or insert targeting entry `i`, `cohCount(i)` is zero and the entry is not immediately eligible for coherence timeout eviction.
- <CK-COH-TIMEOUT-BLOCKED> A coherence-timeout-eligible entry is not selected when a higher-priority condition (miss-queue replay timeout or drain) is active.

#### Miss-Queue Replay Timeout

<FC-REPLAY-TIMEOUT>

An entry that receives a replay response from the DCache sets `w_timeout` and increments `missqReplayCount` each cycle while inflight. Once the counter reaches the threshold, the entry is selected for retry with highest eviction priority.

**Check points:**
- <CK-REPLAY-TIMEOUT-WAIT> After a replay response fire, the entry's `w_timeout` is set and `missqReplayCount` increments from zero until the top bit is set.
- <CK-REPLAY-TIMEOUT-RETRY> When `missqReplayCount` top bit is set, the entry appears in `missqReplayTimeOutMask` and is selected for eviction ahead of all other conditions.
- <CK-REPLAY-TIMEOUT-DEASSERT> After the retry eviction fires (`sbuffer_out_s0_fire`), the `missqReplayHasTimeOut` signal is deasserted.

### Difftest Event Generation

<FG-DIFFTEST>

- **Overview**: When `EnableDifftest` is true, the Sbuffer generates `DiffStoreEvent` traces for every store committed to the DCache. The events capture the store address, data, mask, hart ID, ROB index, and PC for functional verification against the NEMU reference model. Vector stores are re-split into double-word-aligned chunks. Non-cacheable stores to main memory are also traced.
- **Boundaries and Exceptions**: (1) Difftest events are generated only when `env.EnableDifftest` is true. (2) The `DiffSbufferEvent` path emits one event per hit response; the `DiffStoreEvent` path emits per-enqueue-channel events. (3) Vector mask-store (isVsm) and segment-store (isSegment) instructions are excluded from the VSLine split flow.
- **Performance and Constraints**: Difftest event generation does not affect functional correctness; it is an instrumentation-only path.

#### DCache Hit Difftest Event

<FC-DIFF-HIT>

On every DCache hit response fire, a `DiffSbufferEvent` is emitted containing the hart ID, response index, address reconstructed from the ptag, the full cache-line data, and the full mask.

**Check points:**
- <CK-DIFF-HIT-EMIT> For every hit response that fires, exactly one `DiffSbufferEvent` is emitted in the following cycle.
- <CK-DIFF-HIT-DATA> The `DiffSbufferEvent` address equals `getAddr(ptag(resp_id))`; data matches the SbufferData output for the evicted entry.

#### Scalar and Vector Store Difftest Event

<FC-DIFF-STORE>

For each enqueue channel, `DiffStoreEvent` instances are generated. Scalar (non-wline, non-VSLine) stores emit one event with word-aligned address and shifted data. Vector unit-stride and whole-register stores emit chunked events aligned to the element size. Full-line writes emit a series of word-sized events.

**Check points:**
- <CK-DIFF-STORE-SCALAR> For a scalar store fire, exactly one `DiffStoreEvent` is emitted with address, data, and mask derived from `pmaStore` after word alignment.
- <CK-DIFF-STORE-VECTOR-SPLIT> For a vector unit-stride store (`isVSLine`), the number of `DiffStoreEvent` instances equals `flow = 16 >> eew`, each targeting a distinct double-word-aligned address.
- <CK-DIFF-STORE-WLINE> For a full-line write (`isWline`), `WlineMaxNumber` word-sized events are emitted starting at `blockAddr`, each with full-word mask.

### Verification API

<FG-API>

- **Overview**: The test-API functional group covers the standard interfaces and hooks needed to verify the Sbuffer: a driver for enqueuing store requests, a monitor for observing eviction and forwarding events, and a reference-model hook for difftest comparison.
- **Boundaries and Exceptions**: None (test interface).
- **Performance and Constraints**: None (test interface).

#### Driver Interface

<FC-DRIVER>

The testbench driver must drive the `io.in` Decoupled interface with `DCacheWordReqWithVaddrAndPfFlag` payloads and observe the `ready` backpressure signal. It must also drive `io.flush`, `io.forward`, `io.sqempty`, `io.csrCtrl`, `io.force_write`, `io.diffStore`, and `io.memSetPattenDetected`.

**Check points:**
- <CK-DRIVER-ENQ> The driver asserts `io.in(i).valid` with legal request fields; the Sbuffer asserts `ready` when insertion or merge is possible.
- <CK-DRIVER-FLUSH> The driver asserts `io.flush.valid` and observes `io.flush.empty` to determine drain completion.

#### Monitor Interface

<FC-MONITOR>

The testbench monitor must observe `io.dcache.req` for eviction events, `io.dcache.hit_resps` and `io.dcache.replay_resp` for response events, `io.forward[i]` output fields for forwarding events, `io.sbempty` and `io.flush.empty` for status, and the FSM state (via observable outputs) for state tracking.

**Check points:**
- <CK-MONITOR-EVICTION> The monitor captures every `io.dcache.req` fire and records the address, data, mask, and entry ID.
- <CK-MONITOR-FORWARD> The monitor captures every forward query's `matchInvalid`, `forwardMask`, and `forwardData` outputs.

#### Reference Model Hook

<FC-REFMODEL>

When difftest is enabled, the testbench connects the `DiffSbufferEvent` and `DiffStoreEvent` outputs to the reference model (NEMU) for cycle-accurate comparison.

**Check points:**
- <CK-REFMODEL-DIFF-EVENTS> Every diff event emitted by the Sbuffer is consumed by the reference model with matching coreid, address, data, and mask.
- <CK-REFMODEL-ALL-EVENTS> The total count of diff events generated per committed store matches the reference model's expectations (scalar: 1; vector unit-stride: `flow`; wline: `WlineMaxNumber`; nc-store: 1).

### Subcomponent Description

#### Component SbufferData

`SbufferData` is a register-file submodule instantiated by the Sbuffer to store per-entry write data and byte-level write masks. The Sbuffer writes into `SbufferData` via the `writeReq` Valid interface (using `DataWriteReq` fields: wvec, mask, data, vwordOffset, wline) and reads data/mask via `dataOut` and `maskOut` wires, indexed by the eviction pipeline. The Sbuffer also sends mask-flush requests via `maskFlushReq` on each hit response to clear the masks of the completed entry.

The observable behavior relied upon:
- A `writeReq` fire with a valid `wvec` (one-hot) and `vwordOffset` updates the targeted entry at the specified vector-word offset with the supplied data and byte-level mask.
- When `wline` is asserted, the entire cache line for the targeted entry is written (mask is treated as all-ones).
- `dataOut(idx)` returns the full cache-line data for entry `idx` as a packed `UInt`.
- `maskOut(idx)` returns the full byte-level mask for entry `idx` as a packed `UInt`.
- A `maskFlushReq` fire with a valid `wvec` clears all mask bytes for the targeted entry (all bits set to false).

#### Component StorePfWrapper

`StorePfWrapper` is a store-prefetch wrapper submodule that receives enqueue notifications from the Sbuffer and generates prefetch requests to the DCache. The Sbuffer drives `prefetcher.io.sbuffer_enq(i)` with valid and vaddr on each `io.in(i)` fire where `vecValid` is true (when `EnableStorePrefetchSPB` is enabled). It connects `prefetcher.io.prefetch_req(i)` to `io.store_prefetch(i)` according to the `EnableStorePrefetchAtCommit` parameter, and forwards `io.memSetPattenDetected` to the prefetcher.

The observable behavior relied upon:
- When `EnableStorePrefetchSPB` is true, each `io.in(i).fire && vecValid` cycle causes the prefetcher to be trained with the request's vaddr.
- When `EnableStorePrefetchAtCommit` is true, the prefetcher's `prefetch_req(i)` output is ORed with the commit-side trigger (via `io.in(i).fire && vecValid`) to produce `io.store_prefetch(i).valid`.
- The prefetcher's `prefetch_req` outputs use a standard Decoupled handshake; the prefetcher deasserts `ready` when it cannot accept more training data.

### Configuration Registers and Storage

| Register Name/Address | Access Attribute | Bit Field | Default | Description | Read/Write Side Effects |
| ------------- | -------- | ---- | ------ | ---- | ---------- |
| StoreBufferThreshold | Internal constant | 5 bits | 7 via Constantin | Eviction threshold for ActiveCount comparison | None (compile-time constant per hart) |
| StoreBufferBase | Internal constant | 5 bits | 4 via Constantin | Base value subtracted from threshold when `force_write` is asserted | None (compile-time constant per hart) |

- **Register Map Base Address**: No direct bus interface.
- **Configuration Flow**: The eviction threshold is set at elaboration time via `Constantin.createRecord` and is per-hart-configurable. The threshold determines when `do_eviction` is asserted: when `ActiveCount >= threshold` or `ActiveCount == (StoreBufferSize-1)` or `ValidCount == StoreBufferSize`. When `io.force_write` is asserted, the effective threshold becomes `threshold - base`.

### Reset and Error Handling

- **Reset Behavior**: After reset: (1) All Sbuffer entries are in invalid state (`state_valid = false`, `state_inflight = false`, `w_timeout = false`, `w_sameblock_inflight = false`). (2) All per-entry registers (`ptag`, `vtag`, `cohCount`, `missqReplayCount`) are zero. (3) `sbuffer_state` is `x_idle`. (4) `sbempty` and `flush.empty` are asserted. (5) `enbufferSelReg` is false. (6) The sbuffer_out_s1_valid pipeline register is false. (7) All PLRU state is initialized to its reset value.

- **Error Reporting**: (1) `forward.matchInvalid` reports a vtag/ptag mismatch that indicates a potential address-translation inconsistency between the store and load pipelines. (2) Assertions in the source code check invariants: no more than one same-block inflight entry, no PLRU inconsistency, no merge-mask popcount > 1, no invalid-state inflight on response, and no dcache-req-candidate selection when same-block-inflight is asserted.

- **Self-Recovery Strategy**: (1) On vtag/ptag mismatch (`matchInvalid`): the Sbuffer triggers a micro-architectural drain (`x_drain_sbuffer`), blocking new enqueues and flushing existing entries to the DCache. (2) On replay response: the entry sets `w_timeout` and waits for the miss-queue replay counter to reach its threshold before retrying the eviction. (3) There is no software-visible error interrupt; all error conditions are handled by hardware self-recovery (drain or replay retry).

### Parameterization and Configurable Features

- **Module Parameters**:

| Parameter Name | Type/Range | Default | Functional Effect |
| ------ | ------------- | ------ | -------- |
| StoreBufferSize | Int | via XSCoreParamsKey | Number of store-buffer entries; determines index width, counter widths, and PLRU size |
| EnbufferWidth | Int | via XSCoreParamsKey | Number of parallel store-queue input channels; restricts merge/insert parallelism |
| LoadPipelineWidth | Int | via XSCoreParamsKey | Number of load pipeline forward query channels |
| StorePipelineWidth | Int | via XSCoreParamsKey | Number of store prefetch output channels; must be >= EnbufferWidth |
| EvictCountBits | Int | log2Up((1<<20) + 1) | Width of coherence timeout counter; determines timeout period |
| MissqReplayCountBits | Int | log2Up(16) + 1 | Width of replay timeout counter; determines retry delay |
| EnableStorePrefetchSPB | Boolean | via config | Enables training the store prefetcher on sbuffer enqueue events |
| EnableStorePrefetchAtCommit | Boolean | via config | Enables store prefetch requests at commit time |

- **Runtime Configuration**: `io.force_write` lowers the eviction threshold by subtracting `StoreBufferBase` from `StoreBufferThreshold`. The `StoreBufferThreshold` and `StoreBufferBase` values are per-hart compile-time constants set via `Constantin.createRecord`.

- **Compile Macros/Generation Options**: `env.EnableDifftest` controls whether difftest instrumentation logic is generated. When false, `io.diffStore` is tied to `DontCare` and no `DiffSbufferEvent`/`DiffStoreEvent` instances are emitted.

## Verification Requirements and Coverage Suggestions

- **Functional Coverage Points**:
  - Enqueue coverage: insert vs merge per input channel, dual-input with same/different tags, backpressure when full/draining, merge with matching/non-matching vtag.
  - Eviction coverage: arbitration priority (all four conditions), same-block-inflight blocking, write-hazard blocking, PLRU selection across all candidate entries.
  - Response coverage: hit response invalidates entry, replay response sets w_timeout, replay retry after timeout.
  - Forward coverage: data from active entry, data from inflight entry, active-over-inflight priority, no-match case, matchInvalid assertion, matchInvalid deassertion.
  - Timeout coverage: coherence timeout fires after expected interval, replay timeout fires after expected interval.
  - Difftest coverage: DiffSbufferEvent on each hit, DiffStoreEvent for scalar/vector/wline/nc-store, correct event counts.
- **Constraints and Assumptions**:
  1. Input valid signals (`io.in(i).valid`) may be asserted only when the request fields are stable and driven to legal values. The Sbuffer does not sample inputs unless valid is asserted.
  2. The DCache must eventually respond to every accepted write request with either a hit or a replay response. A write request must not be left unanswered indefinitely.
  3. The flush controller must not deassert `flush.valid` before the Sbuffer asserts `flush.empty`; otherwise the drain may not complete.
  4. The store queue must assert `sqempty` correctly; the Sbuffer uses it to qualify `flush.empty` and the `x_drain_all -> x_idle` transition.
  5. The forward query's `paddr` and `vaddr` must be stable while `forward.valid` is asserted.
- **Test Interfaces**:
  - **Driver**: Drive `io.in[i]` with Decoupled handshake (valid + stable bits, observe ready). Drive `io.forward[k]` with Valid handshake (valid + stable vaddr/paddr). Drive `io.flush.valid` and observe `io.flush.empty`. Drive `io.sqempty`, `io.csrCtrl`, `io.force_write`, `io.memSetPattenDetected`, `io.diffStore`.
  - **Monitor**: Observe `io.dcache.req` for eviction write requests. Observe `io.dcache.hit_resps`, `io.dcache.replay_resp`, and `io.dcache.main_pipe_hit_resp` for eviction completions. Observe `io.forward[k].*` outputs for forwarding behavior. Observe `io.store_prefetch[m]` for prefetch requests. Observe `io.sbempty` for buffer status.
  - **Reference Model**: When difftest is enabled, connect `DiffSbufferEvent` and `DiffStoreEvent` to the reference model. The reference model must compare each event against the expected architectural store effect.
  - **Assertions**: The source includes assertion checks for merge mask popcount, PLRU consistency, inflight state on response, and same-block-inflight condition. These assertions should be enabled in simulation and treated as coverage-relevant invariant checks.
