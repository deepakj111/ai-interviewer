/**
 * Client-Side DuckDB-WASM execution runner for zero-server SQL query evaluation.
 */

import * as duckdb from "@duckdb/duckdb-wasm";

let dbInstance: duckdb.AsyncDuckDB | null = null;
let connInstance: duckdb.AsyncDuckDBConnection | null = null;
let initPromise: Promise<duckdb.AsyncDuckDBConnection> | null = null;

export async function getDuckDBConnection(): Promise<duckdb.AsyncDuckDBConnection> {
  if (connInstance) {
    return connInstance;
  }
  if (initPromise) {
    return initPromise;
  }

  initPromise = (async () => {
    // Select best bundle for environment (EH for modern browsers, MVP fallback)
    const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();
    const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);

    const worker_url = URL.createObjectURL(
      new Blob([`importScripts("${bundle.mainWorker!}");`], { type: "text/javascript" })
    );

    const worker = new Worker(worker_url);
    const logger = new duckdb.VoidLogger();
    const db = new duckdb.AsyncDuckDB(logger, worker);
    await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
    URL.revokeObjectURL(worker_url);

    const conn = await db.connect();
    dbInstance = db;
    connInstance = conn;

    // Seed realistic baseline tables
    await seedDefaultAnalyticsTables(conn);

    return conn;
  })();

  return initPromise;
}

export async function seedDefaultAnalyticsTables(conn: duckdb.AsyncDuckDBConnection): Promise<void> {
  const seedScript = `
    CREATE TABLE IF NOT EXISTS users (
        user_id VARCHAR PRIMARY KEY,
        signup_date DATE,
        country VARCHAR
    );

    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id VARCHAR PRIMARY KEY,
        user_id VARCHAR,
        amount DECIMAL(10, 2),
        transaction_date DATE
    );

    CREATE TABLE IF NOT EXISTS events (
        event_id VARCHAR PRIMARY KEY,
        user_id VARCHAR,
        event_time TIMESTAMP,
        event_type VARCHAR
    );

    CREATE TABLE IF NOT EXISTS model_predictions (
        prediction_id VARCHAR PRIMARY KEY,
        user_id VARCHAR,
        predicted_prob DOUBLE,
        actual_label INT
    );
  `;
  await conn.query(seedScript);
}

export interface SQLQueryResult {
  columns: string[];
  rows: (string | number | boolean | null)[][];
  rowCount: number;
  executionTimeMs: number;
}

export async function executeSQLQuery(
  sqlQuery: string,
  customSeedSql?: string
): Promise<SQLQueryResult> {
  const startTime = performance.now();
  const conn = await getDuckDBConnection();

  if (customSeedSql && customSeedSql.trim().length > 0) {
    await conn.query(customSeedSql);
  }

  const result = await conn.query(sqlQuery);
  const executionTimeMs = Math.round(performance.now() - startTime);

  const columns = result.schema.fields.map((f) => f.name);
  const rows: (string | number | boolean | null)[][] = [];

  for (let i = 0; i < result.numRows; i++) {
    const rowObj = result.get(i);
    const rowArr: (string | number | boolean | null)[] = [];
    for (const col of columns) {
      const val = rowObj ? (rowObj as any)[col] : null;
      if (typeof val === "bigint") {
        rowArr.push(Number(val));
      } else {
        rowArr.push(val);
      }
    }
    rows.push(rowArr);
  }

  return {
    columns,
    rows,
    rowCount: rows.length,
    executionTimeMs,
  };
}
