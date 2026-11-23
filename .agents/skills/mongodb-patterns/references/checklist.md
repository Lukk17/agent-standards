# MongoDB Patterns Checklist

Run it before calling a MongoDB change or recommendation done.

- [ ] Deployment shape, topology, server version, and workload known or the assumption stated.
- [ ] The client is constructed once and reused, and in serverless lives outside the handler.
- [ ] Pool and timeout values have reasons, and the server-side connection total was calculated.
- [ ] Real indexes and schema inspected before proposing a new index or model.
- [ ] Compound indexes follow equality, sort, range, and no dead indexes remain.
- [ ] The model follows the access pattern, with no unbounded array and no document near 16MB.
- [ ] Search uses Atlas Search or Vector Search, never `$regex` or `$text`.
- [ ] Hybrid search was version checked before `$rankFusion` or `$scoreFusion` was suggested.
- [ ] No write, index creation, or destructive MCP call ran without explicit approval.
