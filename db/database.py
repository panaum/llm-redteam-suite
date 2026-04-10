import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "redteam.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT UNIQUE NOT NULL,
            model TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            total_attacks INTEGER DEFAULT 0,
            successful_attacks INTEGER DEFAULT 0,
            asr REAL DEFAULT 0.0
        );
        CREATE TABLE IF NOT EXISTS attacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            model TEXT NOT NULL,
            category TEXT NOT NULL,
            technique TEXT NOT NULL,
            prompt TEXT NOT NULL,
            response TEXT NOT NULL,
            success INTEGER NOT NULL,
            score REAL NOT NULL,
            iteration INTEGER DEFAULT 1,
            timestamp TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS successful_bypasses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT NOT NULL,
            category TEXT NOT NULL,
            technique TEXT NOT NULL,
            prompt TEXT NOT NULL,
            score REAL NOT NULL,
            times_used INTEGER DEFAULT 0,
            first_seen TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS asr_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            model TEXT NOT NULL,
            category TEXT NOT NULL,
            asr REAL NOT NULL,
            timestamp TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    print("[DB] Initialized")

def save_run(run_id, model, results):
    conn = get_conn()
    timestamp = datetime.now().isoformat()
    total = len(results)
    successful = sum(1 for r in results if r["success"])
    asr = (successful / total * 100) if total > 0 else 0.0
    conn.execute(
        "INSERT OR REPLACE INTO runs (run_id, model, timestamp, total_attacks, successful_attacks, asr) VALUES (?, ?, ?, ?, ?, ?)",
        (run_id, model, timestamp, total, successful, round(asr, 2))
    )
    for r in results:
        conn.execute(
            "INSERT INTO attacks (run_id, model, category, technique, prompt, response, success, score, iteration, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, model, r["category"], r["technique"], r["prompt"],
             r["response"], int(r["success"]), r["score"], r.get("iteration", 1), timestamp)
        )
        if r["success"]:
            existing = conn.execute(
                "SELECT id FROM successful_bypasses WHERE prompt = ? AND model = ?",
                (r["prompt"], model)
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO successful_bypasses (model, category, technique, prompt, score, first_seen) VALUES (?, ?, ?, ?, ?, ?)",
                    (model, r["category"], r["technique"], r["prompt"], r["score"], timestamp)
                )
    by_category = {}
    for r in results:
        cat = r["category"]
        if cat not in by_category:
            by_category[cat] = {"total": 0, "success": 0}
        by_category[cat]["total"] += 1
        if r["success"]:
            by_category[cat]["success"] += 1
    for cat, counts in by_category.items():
        cat_asr = (counts["success"] / counts["total"] * 100) if counts["total"] > 0 else 0.0
        conn.execute(
            "INSERT INTO asr_history (run_id, model, category, asr, timestamp) VALUES (?, ?, ?, ?, ?)",
            (run_id, model, cat, round(cat_asr, 2), timestamp)
        )
    conn.commit()
    conn.close()
    return asr

def get_past_bypasses(model, category, limit=10):
    conn = get_conn()
    rows = conn.execute(
        "SELECT prompt FROM successful_bypasses WHERE model = ? AND category = ? ORDER BY score DESC LIMIT ?",
        (model, category, limit)
    ).fetchall()
    conn.close()
    return [r["prompt"] for r in rows]

def get_asr_trend(model, category=None, last_n=5):
    conn = get_conn()
    if category:
        rows = conn.execute(
            "SELECT run_id, category, asr, timestamp FROM asr_history WHERE model = ? AND category = ? ORDER BY timestamp DESC LIMIT ?",
            (model, category, last_n)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT run_id, asr, timestamp FROM runs WHERE model = ? ORDER BY timestamp DESC LIMIT ?",
            (model, last_n)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_leaderboard():
    conn = get_conn()
    rows = conn.execute(
        "SELECT model, COUNT(*) as total_runs, AVG(asr) as avg_asr, MIN(asr) as best_asr, MAX(asr) as worst_asr, MAX(timestamp) as last_run FROM runs GROUP BY model ORDER BY avg_asr ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]