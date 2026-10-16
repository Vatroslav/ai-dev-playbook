"use strict";
// In-memory Postgres exposed as a pg-compatible Pool. The test suite runs the real
// production query path (same SQL, $1 placeholders, transactions) with zero infrastructure.
// Usage: const { memPool } = require("./pgmem"); await data.init(memPool());
// Requires the dev dependency `pg-mem`. Each call returns a fresh, isolated database.
const { newDb } = require("pg-mem");

function memPool() {
  const { Pool } = newDb().adapters.createPg();
  return new Pool();
}

module.exports = { memPool };
