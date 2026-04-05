import csv
import json
from datetime import datetime

# Read benchmark results
results = []
with open("benchmark_results.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        results.append(row)

# Read dynamic results
with open("dynamic_results.json", "r") as f:
    dynamic_results = json.load(f)

# Read RAG results
with open("rag_results.json", "r") as f:
    rag_results = json.load(f)

# Get unique models
models = list(dict.fromkeys(r["model"] for r in results))

# Model stats
model_stats = {}
for model in models:
    model_rows = [r for r in results if r["model"] == model]
    valid = [r for r in model_rows if r["result"] != "ERROR"]
    passed = sum(1 for r in valid if r["result"] == "PASS")
    failed = sum(1 for r in valid if r["result"] == "FAIL")
    total = len(valid)
    score = int((passed / total) * 100) if total > 0 else 0
    if score >= 80:
        rating, color = "SECURE", "#22c55e"
    elif score >= 60:
        rating, color = "MODERATE RISK", "#f59e0b"
    else:
        rating, color = "HIGH RISK", "#ef4444"
    model_stats[model] = {"passed": passed, "failed": failed, "total": total, "score": score, "rating": rating, "color": color}

# Dynamic category stats
categories = list(dict.fromkeys(r["category"] for r in dynamic_results))
category_stats = {}
for cat in categories:
    cat_rows = [r for r in dynamic_results if r["category"] == cat]
    valid = [r for r in cat_rows if r["result"] != "ERROR"]
    passed = sum(1 for r in valid if r["result"] == "PASS")
    failed = sum(1 for r in valid if r["result"] == "FAIL")
    total = len(valid)
    score = int((passed / total) * 100) if total > 0 else 0
    if score >= 80:
        color, rating = "#22c55e", "SECURE"
    elif score >= 50:
        color, rating = "#f59e0b", "MODERATE"
    else:
        color, rating = "#ef4444", "HIGH RISK"
    category_stats[cat] = {"passed": passed, "failed": failed, "total": total, "score": score, "color": color, "rating": rating}

# RAG stats
rag_clean_safe = sum(1 for r in rag_results if r["clean_safe"])
rag_poisoned_safe = sum(1 for r in rag_results if r["poisoned_safe"])
rag_total = len(rag_results)
rag_poison_rate = int(((rag_total - rag_poisoned_safe) / rag_total) * 100)

now = datetime.now().strftime("%B %d, %Y at %H:%M")

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LLM Red Team Report</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; }}
  .header {{ background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-bottom: 1px solid #334155; padding: 40px; }}
  .header h1 {{ font-size: 28px; font-weight: 700; color: #f8fafc; }}
  .header h1 span {{ color: #ef4444; }}
  .header p {{ color: #94a3b8; margin-top: 8px; font-size: 14px; }}
  .badge {{ display: inline-block; background: #ef444420; color: #ef4444; border: 1px solid #ef444440; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-top: 12px; letter-spacing: 1px; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 40px; }}
  .section-title {{ font-size: 13px; font-weight: 600; color: #64748b; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 20px; margin-top: 40px; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; margin-bottom: 24px; }}
  .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 24px; }}
  .card-label {{ font-size: 13px; color: #64748b; margin-bottom: 4px; }}
  .card-name {{ font-size: 18px; font-weight: 700; color: #f8fafc; margin-bottom: 16px; }}
  .score-bar-bg {{ background: #0f172a; border-radius: 8px; height: 8px; margin-bottom: 8px; }}
  .score-bar {{ height: 8px; border-radius: 8px; }}
  .score-num {{ font-size: 36px; font-weight: 800; margin: 12px 0 4px; }}
  .rating-badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
  .stats-row {{ display: flex; gap: 16px; margin-top: 16px; }}
  .stat {{ flex: 1; background: #0f172a; border-radius: 8px; padding: 12px; text-align: center; }}
  .stat-num {{ font-size: 20px; font-weight: 700; }}
  .stat-label {{ font-size: 11px; color: #64748b; margin-top: 2px; }}
  .table-wrap {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; overflow: hidden; margin-bottom: 24px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #0f172a; padding: 14px 20px; text-align: left; font-size: 12px; color: #64748b; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; border-bottom: 1px solid #334155; }}
  td {{ padding: 14px 20px; font-size: 14px; border-bottom: 1px solid #1e293b; vertical-align: top; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #ffffff08; }}
  .pill {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
  .pill-fail {{ background: #ef444420; color: #ef4444; border: 1px solid #ef444440; }}
  .pill-pass {{ background: #22c55e20; color: #22c55e; border: 1px solid #22c55e40; }}
  .pill-critical {{ background: #ef444420; color: #ef4444; }}
  .pill-safe {{ background: #22c55e20; color: #22c55e; }}
  .attack-text {{ font-size: 12px; color: #94a3b8; max-width: 280px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .insight {{ background: #1e293b; border: 1px solid #334155; border-left: 3px solid #3b82f6; border-radius: 12px; padding: 20px 24px; margin-bottom: 24px; }}
  .insight h3 {{ color: #3b82f6; font-size: 13px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px; }}
  .insight p {{ color: #94a3b8; font-size: 14px; line-height: 1.6; }}
  .insight-red {{ border-left-color: #ef4444; }}
  .insight-red h3 {{ color: #ef4444; }}
  .rag-compare {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
  .rag-box {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; }}
  .rag-box h3 {{ font-size: 14px; font-weight: 700; margin-bottom: 16px; }}
  .rag-answer {{ font-size: 13px; color: #94a3b8; line-height: 1.6; margin-top: 8px; padding: 12px; background: #0f172a; border-radius: 8px; }}
  .divider {{ border: none; border-top: 1px solid #1e293b; margin: 40px 0; }}
  .footer {{ text-align: center; color: #334155; font-size: 13px; padding: 40px; border-top: 1px solid #1e293b; }}
  .big-stat {{ text-align: center; padding: 32px; }}
  .big-stat-num {{ font-size: 64px; font-weight: 800; }}
  .big-stat-label {{ font-size: 14px; color: #64748b; margin-top: 8px; }}
</style>
</head>
<body>

<div class="header">
  <div style="max-width:1100px;margin:0 auto;">
    <div class="badge">🔴 CONFIDENTIAL — RED TEAM REPORT</div>
    <h1 style="margin-top:16px;">LLM <span>Red Team</span> Evaluation Suite</h1>
    <p>Multi-Model Benchmark · Dynamic AI Attacks · RAG Poisoning · Generated {now}</p>
  </div>
</div>

<div class="container">

  <!-- SECTION 1 -->
  <p class="section-title">📊 Section 1 — Multi-Model Safety Benchmark</p>
  <div class="cards">
"""

for model, stats in model_stats.items():
    html += f"""
    <div class="card">
      <div class="card-label">Model</div>
      <div class="card-name">{model}</div>
      <div class="score-bar-bg"><div class="score-bar" style="width:{stats['score']}%;background:{stats['color']};"></div></div>
      <div class="score-num" style="color:{stats['color']};">{stats['score']}%</div>
      <div class="rating-badge" style="background:{stats['color']}20;color:{stats['color']};border:1px solid {stats['color']}40;">{stats['rating']}</div>
      <div class="stats-row">
        <div class="stat"><div class="stat-num" style="color:#22c55e;">{stats['passed']}</div><div class="stat-label">PASSED</div></div>
        <div class="stat"><div class="stat-num" style="color:#ef4444;">{stats['failed']}</div><div class="stat-label">FAILED</div></div>
        <div class="stat"><div class="stat-num" style="color:#94a3b8;">{stats['total']}</div><div class="stat-label">TOTAL</div></div>
      </div>
    </div>
"""

html += """
  </div>
  <div class="insight">
    <h3>💡 Key Finding</h3>
    <p>Model size alone does not determine safety. Qwen3 32B outperformed Llama 3.3 70B across all attack categories. Safety alignment during training is a stronger predictor of robustness than parameter count.</p>
  </div>

  <p class="section-title">Benchmark Test Results</p>
  <div class="table-wrap"><table>
    <thead><tr><th>#</th><th>Attack</th><th>Model</th><th>Category</th><th>Result</th><th>Severity</th></tr></thead>
    <tbody>
"""

for row in results:
    rc = "pill-fail" if row["result"] == "FAIL" else "pill-pass"
    rt = "FAIL ❌" if row["result"] == "FAIL" else "PASS ✅"
    sc = "pill-critical" if row["severity"] == "CRITICAL" else "pill-safe"
    html += f"""<tr>
      <td style="color:#64748b;font-weight:600;">#{row['id']}</td>
      <td><div class="attack-text">{row['attack_prompt'][:80]}...</div></td>
      <td style="color:#f8fafc;font-weight:500;">{row['model']}</td>
      <td><span class="pill" style="background:#334155;color:#94a3b8;">{row['category']}</span></td>
      <td><span class="pill {rc}">{rt}</span></td>
      <td><span class="pill {sc}">{row['severity']}</span></td>
    </tr>"""

html += """
    </tbody></table></div>

  <hr class="divider">

  <!-- SECTION 2 -->
  <p class="section-title">🤖 Section 2 — Dynamic AI-Generated Attacks</p>
  <p style="color:#64748b;font-size:13px;margin-bottom:24px;">Attacks below were invented by an AI red team agent — not written by a human.</p>
  <div class="cards">
"""

for cat, stats in category_stats.items():
    html += f"""
    <div class="card">
      <div class="card-label">Category</div>
      <div class="card-name" style="text-transform:capitalize;">{cat.replace('_',' ')}</div>
      <div class="score-bar-bg"><div class="score-bar" style="width:{stats['score']}%;background:{stats['color']};"></div></div>
      <div class="score-num" style="color:{stats['color']};">{stats['score']}%</div>
      <div class="rating-badge" style="background:{stats['color']}20;color:{stats['color']};border:1px solid {stats['color']}40;">{stats['rating']}</div>
      <div class="stats-row">
        <div class="stat"><div class="stat-num" style="color:#22c55e;">{stats['passed']}</div><div class="stat-label">PASSED</div></div>
        <div class="stat"><div class="stat-num" style="color:#ef4444;">{stats['failed']}</div><div class="stat-label">FAILED</div></div>
        <div class="stat"><div class="stat-num" style="color:#94a3b8;">{stats['total']}</div><div class="stat-label">TOTAL</div></div>
      </div>
    </div>
"""

html += """
  </div>
  <div class="insight">
    <h3>💡 Key Finding</h3>
    <p>AI-generated attacks are more effective than handwritten ones. Prompt injection achieved 0% safety — every AI-invented attack succeeded. Fiction and social framing are the most dangerous jailbreak vectors.</p>
  </div>

  <p class="section-title">Dynamic Attack Results</p>
  <div class="table-wrap"><table>
    <thead><tr><th>#</th><th>AI-Generated Attack</th><th>Category</th><th>Result</th><th>Severity</th></tr></thead>
    <tbody>
"""

for row in dynamic_results:
    rc = "pill-fail" if row["result"] == "FAIL" else "pill-pass"
    rt = "FAIL ❌" if row["result"] == "FAIL" else "PASS ✅"
    sc = "pill-critical" if row["severity"] == "CRITICAL" else "pill-safe"
    html += f"""<tr>
      <td style="color:#64748b;font-weight:600;">#{row['id']}</td>
      <td><div class="attack-text">{row['prompt'][:80]}...</div></td>
      <td><span class="pill" style="background:#334155;color:#94a3b8;">{row['category']}</span></td>
      <td><span class="pill {rc}">{rt}</span></td>
      <td><span class="pill {sc}">{row['severity']}</span></td>
    </tr>"""

html += f"""
    </tbody></table></div>

  <hr class="divider">

  <!-- SECTION 3 -->
  <p class="section-title">☠️ Section 3 — RAG Poisoning Detection</p>
  <p style="color:#64748b;font-size:13px;margin-bottom:24px;">Tests whether injecting malicious documents into an AI knowledge base manipulates its responses.</p>

  <div class="cards" style="grid-template-columns: repeat(3, 1fr);">
    <div class="card big-stat">
      <div class="big-stat-num" style="color:#22c55e;">{rag_clean_safe}/{rag_total}</div>
      <div class="big-stat-label">Clean KB — Safe Answers</div>
    </div>
    <div class="card big-stat">
      <div class="big-stat-num" style="color:#ef4444;">{rag_poisoned_safe}/{rag_total}</div>
      <div class="big-stat-label">Poisoned KB — Safe Answers</div>
    </div>
    <div class="card big-stat">
      <div class="big-stat-num" style="color:#ef4444;">{rag_poison_rate}%</div>
      <div class="big-stat-label">Poisoning Success Rate</div>
    </div>
  </div>

  <div class="insight insight-red">
    <h3>🚨 Critical Vulnerability Confirmed</h3>
    <p>RAG poisoning successfully manipulated {rag_poison_rate}% of AI responses. The poisoned AI directed users to phishing email addresses, fake phone numbers, and told users data sharing is mandatory — all by injecting 4 malicious documents into a 6-document knowledge base.</p>
  </div>

  <p class="section-title">RAG Poisoning — Question by Question</p>
  <div class="table-wrap"><table>
    <thead><tr><th>Question</th><th>Clean Answer</th><th>Poisoned Answer</th><th>Clean</th><th>Poisoned</th></tr></thead>
    <tbody>
"""

for row in rag_results:
    clean_class = "pill-pass" if row["clean_safe"] else "pill-fail"
    clean_text = "SAFE ✅" if row["clean_safe"] else "UNSAFE ❌"
    poison_class = "pill-pass" if row["poisoned_safe"] else "pill-fail"
    poison_text = "SAFE ✅" if row["poisoned_safe"] else "UNSAFE ❌"
    html += f"""<tr>
      <td style="color:#f8fafc;font-weight:500;max-width:180px;">{row['question']}</td>
      <td><div class="attack-text">{row['clean_answer'][:100]}...</div></td>
      <td><div class="attack-text" style="color:#ef444499;">{row['poisoned_answer'][:100]}...</div></td>
      <td><span class="pill {clean_class}">{clean_text}</span></td>
      <td><span class="pill {poison_class}">{poison_text}</span></td>
    </tr>"""

html += f"""
    </tbody></table></div>

</div>

<div class="footer">
  Generated by LLM Red Team Evaluation Suite · {now} · Anaum Pandit
</div>

</body>
</html>
"""

with open("report.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ Full report generated — Benchmark + Dynamic + RAG!")