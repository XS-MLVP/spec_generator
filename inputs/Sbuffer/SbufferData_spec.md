# SbufferData Specification Document

> This document describes the specification of the `SbufferData` chip verification target. Keep the technical language precise, well-organized, and easy to reuse for verification. If an item does not exist, explicitly write "None" or "TBD"; do not delete the section.

## Introduction

- **Design Background**: `SbufferData` is a register-file submodule within the XiangShan CPU memory subsystem. It is instantiated by the top-level `Sbuffer` module to hold the per-entry write data and byte-level write masks for all `StoreBufferSize` store-buffer entries. The `Sbuffer` module writes data on every enqueue (insert or merge), reads data during eviction to assemble the DCache write request, and clears mask bytes after a successful DCache write.
- **Design Goals**: (1) Provide byte-addressable write storage for `StoreBufferSize` entries, each holding a full cache line of data and byte-level mask. (2) Support word-offset-addressable writes with byte-level mask enables. (3) Support full-cache-line reads for eviction. (4) Support clearing of all mask bytes for a given entry on mask-flush request. (5) Provide combinational read access for load-forwarding and eviction pipelines.

## Terms and Abbreviations in Chisel Code

| Abbreviation | Full Term | Description |
| ---- | ---- | ---- |
| wvec | Write Vector | One-hot vector of width `StoreBufferSize` selecting which entry to write |
| vwordOffset | Vector-Word Offset | Offset within the cache line selecting which vector word to write |
| wline | Write Line | When asserted, the full cache line is written regardless of the byte mask |
| VLEN | Vector Data Width (bits) | Width of the vector data bus; each entry stores VLEN bits of data and VLEN/8 bits of mask |
| VDataBytes | Vector Data Bytes | VLEN / 8; number of bytes per vector word |
| CacheLineVWords | Cache-Line Vector Words | CacheLineBytes / VDataBytes; number of vector words per cache line |
| EnsbufferWidth | Enqueue Buffer Width | Number of parallel write-request channels from the Sbuffer enqueue logic |
| NumDcacheWriteResp | DCache Write Response Count | Number of mask-flush request channels from the Sbuffer response logic |

## Chisel Source Files

File list:
- `fm_agent/extracted_functions/Sbuffer-scala/SbufferData.scala`: The `SbufferData` module containing the register-file storage, write, read, and mask-flush logic (93 lines).
- `fm_agent/extracted_functions/Sbuffer-scala/DataWriteReq.scala`: Bundle type for write-request payload (wvec, mask, data, vwordOffset, wline).
- `fm_agent/extracted_functions/Sbuffer-scala/MaskFlushReq.scala`: Bundle type for mask-flush request payload (wvec).
- `fm_agent/extracted_functions/Sbuffer-scala/HasSbufferConst.scala`: Trait providing width parameters (`StoreBufferSize`, `CacheLineVWords`, `VDataBytes`, etc.).

## Top-Level Interface Overview

- **Module Name**: `SbufferData`

- **Port List**:

| Signal Name | Direction | Width/Type | Reset Value | Description |
| ------ | ---- | -------- | ------ | ---- |
| clock | input | Clock | N/A | Clock signal |
| reset | input | Reset | N/A | Reset signal |
| writeReq[i].valid | input | Bool, x EnsbufferWidth | N/A | Valid for a data/mask write operation on channel `i` |
| writeReq[i].bits.wvec | input | UInt(StoreBufferSize.W) | N/A | One-hot select of the entry to write |
| writeReq[i].bits.mask | input | UInt(VLEN/8.W) | N/A | Byte-level write mask; only bytes with mask(byte)=true are written |
| writeReq[i].bits.data | input | UInt(VLEN.W) | N/A | Write data |
| writeReq[i].bits.vwordOffset | input | UInt(VWordOffsetWidth.W) | N/A | Vector-word offset within the cache line |
| writeReq[i].bits.wline | input | Bool | N/A | Full-line write override; when asserted the entire cache line is written |
| maskFlushReq[j].valid | input | Bool, x NumDcacheWriteResp | N/A | Valid for a mask-flush operation on channel `j` |
| maskFlushReq[j].bits.wvec | input | UInt(StoreBufferSize.W) | N/A | One-hot select of the entry whose mask to clear |
| dataOut[i] | output | Vec(CacheLineVWords, Vec(VDataBytes, UInt(8.W))), x StoreBufferSize | all-zero | Full cache-line data for entry `i`; combinational read |
| maskOut[i] | output | Vec(CacheLineVWords, Vec(VDataBytes, Bool())), x StoreBufferSize | all-false | Full byte-level mask for entry `i`; combinational read |

- **Clock and Reset Requirements**: Single implicit clock domain. Synchronous reset. After reset all data registers are zero and all mask registers are false.

- **External Dependencies**: (1) The Sbuffer must ensure that `writeReq[i].valid` and `maskFlushReq[j].valid` are not asserted simultaneously targeting the same entry index in the same cycle. (2) The Sbuffer must ensure that `wvec` is one-hot (exactly one bit set) when `writeReq[i].valid` or `maskFlushReq[j].valid` is asserted. (3) The Sbuffer read pipeline must not read an entry (`dataOut[i]`, `maskOut[i]`) in the same cycle that entry is being written (the 2-cycle pipeline delay prevents this hazard by construction).

## Functional Description

### Data Write Operation

<FG-DATA-WRITE>

- **Overview**: The SbufferData module accepts write requests via the `writeReq[i]` Valid interface. Each write targets one entry (selected by the one-hot `wvec`), at one vector-word offset (`vwordOffset`), with byte-level enables (`mask`) and data (`data`). When `wline` is asserted, the full cache line is written independently of `mask` and `vwordOffset`. Writes are registered through a 2-cycle pipeline before being committed to storage.
- **Boundaries and Exceptions**: (1) If `wline` is asserted, the full cache line is written, overriding `vwordOffset` and `mask` (every byte is written and every mask bit is set to true). (2) If `wvec` has more than one bit set, behavior is undefined (the Sbuffer asserts that `wvec` is one-hot). (3) Each write channel operates independently; concurrent writes targeting the same entry from different channels produce TBD behavior (the Sbuffer avoids this by construction).
- **Performance and Constraints**: Up to `EnsbufferWidth` write requests accepted simultaneously. Writes complete and are observable 2 cycles after `valid` assertion. Data and mask are captured at the same pipeline stage to ensure consistency.

#### Write with Byte-Level Mask

<FC-WRITE-MASKED>

When `writeReq[i].valid` is asserted with `wline == false` and a valid one-hot `wvec`, the bytes of the targeted entry at `vwordOffset` for which `mask` bits are set are updated with the corresponding bytes of `data`. Bytes for which `mask` is not set retain their previous value. After the 2-cycle pipeline delay, the updated values are observable on `dataOut[entryIdx]` and `maskOut[entryIdx]`.

**Check points:**
- <CK-WRITE-MASKED-DATA> After a masked write fires, `dataOut[entryIdx]` at the written vector-word offset reflects the written data bytes; bytes outside the mask are unchanged from their previous value.
- <CK-WRITE-MASKED-MASK> After a masked write fires, `maskOut[entryIdx]` at the written vector-word offset has true bits exactly at the byte positions where `mask` was set; other bits retain their previous state.
- <CK-WRITE-MASKED-OTHER-ENTRIES> A masked write to entry `A` does not modify the data or mask storage of any other entry `B` (B != A).
- <CK-WRITE-MASKED-2CYCLE-LATENCY> A write whose `valid` is asserted in cycle `T` is observable on `dataOut` and `maskOut` starting at cycle `T+2`.

#### Full-Line Write

<FC-WRITE-WLINE>

When `writeReq[i].valid` is asserted with `wline == true` and a valid one-hot `wvec`, all bytes of the targeted entry are overwritten with `data`, independent of `vwordOffset` and `mask`. The mask storage for all bytes of the entry is set to true. After the 2-cycle pipeline delay, the full entry reflects the written data and all-true mask.

**Check points:**
- <CK-WRITE-WLINE-DATA> After a full-line write fires, all bytes of `dataOut[entryIdx]` equal the corresponding bytes of `data` from the write request, across all vector-word offsets.
- <CK-WRITE-WLINE-MASK> After a full-line write fires, all bits of `maskOut[entryIdx]` are true across all vector-word offsets.
- <CK-WRITE-WLINE-VWORD-IGNORED> The `vwordOffset` field has no effect on the written data or mask when `wline` is true.

### Mask Flush Operation

<FG-MASK-FLUSH>

- **Overview**: The SbufferData module accepts mask-flush requests via the `maskFlushReq[j]` Valid interface. Each flush targets one entry (selected by the one-hot `wvec`) and clears all mask bytes for that entry. The mask-flush is triggered by a DCache hit response: the Sbuffer asserts `maskFlushReq[j].valid` with the completed entry's index.
- **Boundaries and Exceptions**: (1) Mask flush does not modify data storage. (2) If `wvec` has more than one bit set, behavior is undefined. (3) A mask flush and a data write targeting the same entry in the same cycle must not conflict (the Sbuffer ensures they do not occur simultaneously for the same entry).
- **Performance and Constraints**: Mask flush completes and is observable 1 cycle after the flag assertion propagates through the `GatedValidRegNext` pipeline. The flush applies to all vector words and all bytes of the selected entry.

#### Entry Mask Clear

<FC-MASK-CLEAR>

When `maskFlushReq[j].valid` is asserted with a valid one-hot `wvec`, all mask bytes for the selected entry are set to false after a 1-cycle pipeline delay.

**Check points:**
- <CK-MASK-CLEAR-ALL-ZERO> After a mask-flush fire on entry `idx`, all bits of `maskOut[idx]` are false across all vector-word offsets.
- <CK-MASK-CLEAR-DATA-UNCHANGED> After a mask-flush fire on entry `idx`, the `dataOut[idx]` values are unchanged.
- <CK-MASK-CLEAR-1CYCLE-LATENCY> A mask-flush whose `valid` is asserted in cycle `T` is observable on `maskOut` starting at cycle `T+1`.

### Data Read Operation

<FG-DATA-READ>

- **Overview**: The Sbuffer reads the full cache-line data and mask for a given entry via `dataOut(i)` and `maskOut(i)`. These are combinational (wire) reads from the register-file output ports — there is no read-enable signal and no read-side pipeline.
- **Boundaries and Exceptions**: A read of an entry that is being written in the same cycle returns the pre-update value (write happens in the 2-cycle-delayed pipeline stage, so the read sees the old value until the pipeline commits).
- **Performance and Constraints**: `dataOut(i)` and `maskOut(i)` are available combinatorially: no setup or hold requirement beyond the register-file read access time.

#### Combinational Entry Read

<FC-READ-COMB>

At any cycle, the output ports `dataOut(i)` and `maskOut(i)` present the current stored data and mask for entry `i` without requiring an explicit read request.

**Check points:**
- <CK-READ-COMB-DATA> `dataOut(i)` equals the current register-file data for entry `i` in all cycles.
- <CK-READ-COMB-MASK> `maskOut(i)` equals the current register-file mask for entry `i` in all cycles.
- <CK-READ-COMB-NO-READY> No handshake or ready signal is required: `dataOut` and `maskOut` are always valid.

### Test and Verification API

<FG-API>

- **Overview**: The test-API functional group covers the standard interfaces and hooks needed to verify the SbufferData module: a driver for injecting write and mask-flush requests, a monitor for observing entry state, and a reference-model scoreboard for correctness checking.
- **Execution Flow**: None (test interface).
- **Boundaries and Exceptions**: None (test interface).
- **Performance and Constraints**: None (test interface).

#### Driver Interface

<FC-DRIVER>

The testbench driver must drive the `writeReq[i]` Valid interface with `DataWriteReq` payloads (wvec, mask, data, vwordOffset, wline) and the `maskFlushReq[j]` Valid interface with `MaskFlushReq` payloads (wvec). The driver must ensure one-hot wvec and mutually exclusive write/mask-flush to the same entry.

**Check points:**
- <CK-DRIVER-WRITE> The driver asserts `writeReq[i].valid` with legal one-hot wvec and stable data/mask/vwordOffset/wline fields.
- <CK-DRIVER-MASK-FLUSH> The driver asserts `maskFlushReq[j].valid` with a legal one-hot wvec.

#### Monitor Interface

<FC-MONITOR>

The testbench monitor must observe `dataOut[i]` and `maskOut[i]` for every entry `i` at any cycle, capturing the combinational read values for comparison against expected state.

**Check points:**
- <CK-MONITOR-READ> The monitor captures `dataOut[i]` and `maskOut[i]` at a sample point and records the full entry state for all `StoreBufferSize` entries.

#### Reference Model Hook

<FC-REFMODEL>

A scoreboard reference model tracks the expected data and mask per entry after each write and mask-flush operation, accounting for the 2-cycle write pipeline and 1-cycle mask-flush pipeline latencies. The testbench compares the scoreboard state against `dataOut` and `maskOut` at any observation point.

**Check points:**
- <CK-REFMODEL-WRITE> After a write request with known data and mask, the scoreboard updates its expected entry state and matches `dataOut`/`maskOut` after the pipeline latency.
- <CK-REFMODEL-MASK-FLUSH> After a mask-flush request, the scoreboard clears the expected mask for the entry and matches `maskOut` after the pipeline latency.

### Subcomponent Description

None (`SbufferData` is a leaf storage module with no submodules of its own).

### Configuration Registers and Storage

| Register Name/Address | Access Attribute | Bit Field | Default | Description | Read/Write Side Effects |
| ------------- | -------- | ---- | ------ | ---- | ---------- |
| Entry[i] data | Internal storage | VLEN bits per entry, `StoreBufferSize` entries | 0 | Full cache-line data for entry `i` | Written on `writeReq` fire targeting entry `i` after 2-cycle pipeline |
| Entry[i] mask | Internal storage | VLEN/8 bits per entry, `StoreBufferSize` entries | 0 | Byte-level write mask for entry `i` | Written on `writeReq` fire; cleared on `maskFlushReq` fire |

- **Register Map Base Address**: No direct bus interface.
- **Configuration Flow**: All storage is reset to zero (data) or false (mask). All writes are driven by the Sbuffer enqueue pipeline; all mask flushes are driven by the Sbuffer DCache-response pipeline. The storage width is determined by the `HasSbufferConst` parameters (`StoreBufferSize`, `CacheLineVWords`, `VDataBytes`), which are set at elaboration time.

### Reset and Error Handling

- **Reset Behavior**: After reset: (1) All data registers for all `StoreBufferSize` entries are zero. (2) All mask registers for all `StoreBufferSize` entries are false. (3) All internal pipeline registers (`line_write_buffer_data`, `line_write_buffer_wline`, `line_write_buffer_mask`, `line_write_buffer_offset`) are at their `RegEnable` initial value (DontCare/random).
- **Error Reporting**: None. The module has no error outputs or assertion outputs.
- **Self-Recovery Strategy**: None. The module does not detect or recover from errors; correctness relies on the Sbuffer ensuring proper input timing and one-hot encoding.

### Parameterization and Configurable Features

- **Module Parameters**:

| Parameter Name | Type/Range | Default | Functional Effect |
| ------ | ------------- | ------ | -------- |
| StoreBufferSize | Int | via XSCoreParamsKey | Number of store-buffer entries; determines addressable entry range, width of `wvec`, and number of `dataOut`/`maskOut` ports |
| CacheLineVWords | Int | CacheLineBytes / VDataBytes | Number of vector words per cache line; determines the addressable offset range for `vwordOffset` |
| VDataBytes | Int | VLEN / 8 | Number of bytes per vector word; determines the width of `data`, `mask`, and the per-byte storage array |
| EnsbufferWidth | Int | via XSCoreParamsKey | Number of parallel write-request input channels |
| NumDcacheWriteResp | Int | 1 | Number of mask-flush request input channels |
| VLEN | Int | via core configuration | Vector data width in bits; determines `data` and `mask` bit widths |
| VWordOffsetWidth | Int | log2Up(CacheLineVWords) | Width of the `vwordOffset` field |

- **Runtime Configuration**: None. All parameters are elaboration-time constants.
- **Compile Macros/Generation Options**: None.

## Verification Requirements and Coverage Suggestions

- **Functional Coverage Points**:
  - Write coverage: masked write at each vector-word offset, full-line write, concurrent writes on multiple channels targeting different entries.
  - Mask-flush coverage: mask-flush for each entry, mask-flush followed by write to same entry.
  - Read-after-write coverage: read of an entry N cycles after write (N = 0, 1, 2, 3+) to verify pipeline latency and data persistence.
  - Concurrent-operation coverage: simultaneous write and mask-flush targeting different entries.
  - Reset coverage: data and mask values after reset, read immediately after reset.
  - Boundary coverage: write to last entry (`StoreBufferSize-1`), mask-flush of entry that was never written.

- **Constraints and Assumptions**:
  1. `writeReq[i].valid` must not be asserted unless `wvec` has exactly one bit set.
  2. `maskFlushReq[j].valid` must not be asserted unless `wvec` has exactly one bit set.
  3. `writeReq[i].bits` fields (`data`, `mask`, `vwordOffset`, `wline`) must be stable while `valid` is asserted.
  4. The Sbuffer must not assert `writeReq[i].valid` and `maskFlushReq[j].valid` for the same entry index in the same cycle.
  5. The Sbuffer must not read an entry (`dataOut`, `maskOut`) in the same cycle a write to that entry commits (the 2-cycle pipeline prevents this, but a test that directly drives SbufferData must respect this constraint).

- **Test Interfaces**:
  - **Driver**: Drive `writeReq[i]` with Valid interface (valid + stable bits). Drive `maskFlushReq[j]` with Valid interface (valid + stable wvec).
  - **Monitor**: Observe `dataOut[i]` and `maskOut[i]` at any cycle (combinational read, no handshake).
  - **Reference Model**: A scoreboard tracking the expected data and mask per entry after each write and mask-flush. Compare `dataOut[i]` and `maskOut[i]` against the scoreboard at any sample point.
  - **Assertions**: No in-module assertions; the testbench should verify one-hot wvec invariant and write/mask-flush mutual exclusion.
