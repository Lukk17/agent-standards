# Blockchain and wallet security

Controls for an application that authenticates users by wallet signature or submits on-chain transactions on their
behalf. Depth behind [SKILL.md](../SKILL.md), and only relevant to projects that hold a wallet integration.

The examples use a Solana-style API. The rules translate directly to any chain: the shapes that change are the signature
scheme and the transaction fields, not the checks.

---

### Verify wallet ownership by signature

A public key proves nothing on its own, because anyone can send you one. Ownership is proved by signing a challenge the
server issued.

Fail: the client claims an address and the server believes it.

```typescript
const { publicKey } = await request.json()
const session = await createSession(publicKey)
```

Pass: the server issues a nonce, the wallet signs it, and the server verifies the signature against the claimed key.

```typescript
async function verifyWalletOwnership(publicKey: string, signature: string, message: string) {
  try {
    return verify(
      Buffer.from(message),
      Buffer.from(signature, 'base64'),
      Buffer.from(publicKey, 'base64'),
    )
  } catch {
    return false
  }
}
```

The signed message must contain a server-issued single-use nonce with a short expiry, plus the origin, so a signature
captured on one site cannot be replayed on another or reused later.

---

### Validate every transaction before signing

Never sign or submit a transaction whose fields came from the client unchecked. Recompute the recipient and the amount
server-side from the order the user actually placed.

```typescript
async function verifyTransaction(transaction: Transaction) {
  if (transaction.to !== expectedRecipient) {
    throw new Error('Unexpected recipient')
  }
  if (transaction.amount > maxAmount) {
    throw new Error('Amount exceeds the configured limit')
  }
  const balance = await getBalance(transaction.from)
  if (balance < transaction.amount) {
    throw new Error('Insufficient balance')
  }
  return true
}
```

Blind signing, where the application signs whatever payload it is handed, is the failure behind most wallet-drain
incidents. Every field a signature covers is a field that must be checked first.

---

### Checklist

- [ ] Wallet ownership proved by a signature over a server-issued, single-use, expiring nonce.
- [ ] The signed message names the origin, so signatures cannot be replayed cross-site.
- [ ] Recipient and amount recomputed server-side, never taken from the client.
- [ ] An upper bound enforced on transaction value.
- [ ] Balance checked before submission.
- [ ] No blind signing of a payload the application has not fully inspected.
- [ ] Test suites and any automated flow point at a test network, never mainnet.
