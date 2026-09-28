# Unified Engineering Provenance & SHA-256 Event Chaining

## 1. Overview & Core Principle

The **Engineering Provenance Layer** (introduced in Slice 8L) provides an append-only, tamper-evident audit record spanning the entire software engineering lifecycle.

It connects:
`Request` $\rightarrow$ `Implementation` $\rightarrow$ `Git Commit` $\rightarrow$ `Pull Request` $\rightarrow$ `AI Review` $\rightarrow$ `CI` $\rightarrow$ `Application Context` $\rightarrow$ `Change Impact` $\rightarrow$ `Regression Plan` $\rightarrow$ `Lab Execution` $\rightarrow$ `Evidence` $\rightarrow$ `AI Evaluation` $\rightarrow$ `Diagnosis` $\rightarrow$ `Remediation` $\rightarrow$ `Human Decision` $\rightarrow$ `Authorization` $\rightarrow$ `Independent Retest` $\rightarrow$ `Post-Change Verification`.

---

## 2. Cryptographic Event Chain

```text
Genesis Hash ("0" * 64)
       ↓
Event 1 (Sequence 1)  ───► SHA256(canonical_payload_1 + genesis_hash) = Hash 1
       ↓
Event 2 (Sequence 2)  ───► SHA256(canonical_payload_2 + Hash 1)       = Hash 2
       ↓
Event 3 (Sequence 3)  ───► SHA256(canonical_payload_3 + Hash 2)       = Hash 3
       ↓
      ...
```

### Deterministic Serialization
Every lifecycle event undergoes deterministic canonical JSON serialization:
- All dictionary keys sorted lexicographically (`sort_keys=True`).
- Whitespace stripped from separators (`separators=(',', ':')`).
- Calculated hash fields (`event_hash`, `previous_event_hash`) strictly excluded from the pre-image.

### Mathematical Hash Formula
$$\text{event\_hash} = \text{SHA256}(\text{canonical\_payload} + \text{previous\_event\_hash})$$

---

## 3. Tamper Detection & Audit Guarantees

The `verify_chain()` audit function detects four categories of anomalies:
1. **Payload Modification (`MODIFIED_EVENT`)**: If an event's metadata or attributes in the database are modified post-hoc, recomputing the SHA-256 hash over the row immediately exposes a hash mismatch.
2. **Broken Hash Sequence (`INCORRECT_PREVIOUS_HASH`)**: If an event's `previous_event_hash` does not equal the preceding event's `event_hash`, the chain is flagged as broken.
3. **Event Deletion / Sequence Skip**: If an intermediate event is deleted from SQLite, the subsequent event's `previous_event_hash` points to an absent parent, instantly breaking verification.
4. **Duplicate Events (`DUPLICATE_EVENT`)**: Duplicate event IDs or non-monotonic sequence numbers are identified.

---

## 4. Append-Only Correction Invariant

Historical events in `engineering_lifecycle_events` are **never updated or deleted**. 

When an error in a recorded event must be corrected (e.g. incorrect commit message or amended request description), a new event of type `EVENT_CORRECTION` is appended to the chain. The correction event:
- Cites `parent_event_id` pointing to the event being amended.
- Documents the rationale and updated fields in its metadata.
- Receives a new monotonic sequence number and SHA-256 hash extending the unbroken chain.

---

## 5. What This Is and What It Is Not

- **Tamper-Evident Traceability**: Provenance provides verifiable proof that an engineering trace has not been altered since execution.
- **Not a Blockchain**: It does not implement proof-of-work, consensus algorithms, tokenomics, or decentralized ledgers. It is a local-first cryptographic audit log designed for high-throughput software engineering verification.
