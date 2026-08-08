#!/usr/bin/env python3
"""
Applies a stock-watchlist add/remove request submitted via a GitHub Issue.

How this fits into the "only the repo owner can add/remove stocks" feature:
the dashboard (docs/js/app.js, buildStockRequestIssueUrl()) builds a
pre-filled "New Issue" URL and opens it — the static site itself never asks
for or stores any credential. The actual gatekeeping happens in the GitHub
Action (.github/workflows/stock-request.yml), which only ever runs this
script for issues opened by github.repository_owner; this script does NOT
re-check authorship itself, it trusts the workflow's `if:` condition.

Reads the issue body from the ISSUE_BODY environment variable — never
interpolated directly into a shell command by the calling workflow — to
avoid script-injection from issue content.

Exit codes:
  0 = applied successfully; a human-readable confirmation is printed to
      stdout for the workflow to post as an issue comment.
  1 = not a stock-request issue at all (no recognized marker) — the
      workflow should skip silently (e.g. the owner opened an unrelated
      bug-report issue).
  2 = looked like a stock-request but was invalid or a no-op (bad market,
      missing fields, duplicate add, remove of a symbol that isn't tracked)
      — an explanation is printed to stderr for the workflow to post as an
      issue comment so the owner can fix and reopen/re-file.
"""
import os
import sys
import json
import re

MARKER = "<!-- stock-request -->"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json")
VALID_MARKETS = ("TW", "US")


def parse_fields(body: str) -> dict:
    """Extract ACTION/SYMBOL/NAME/MARKET key:value lines from the issue body."""
    fields = {}
    for line in body.splitlines():
        m = re.match(r"^\s*(ACTION|SYMBOL|NAME|MARKET)\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
        if m:
            fields[m.group(1).upper()] = m.group(2).strip()
    return fields


def main():
    body = os.environ.get("ISSUE_BODY") or ""

    if MARKER not in body:
        print("not a stock-request issue (no marker found)", file=sys.stderr)
        sys.exit(1)

    fields = parse_fields(body)
    action = (fields.get("ACTION") or "").strip().lower()
    symbol = (fields.get("SYMBOL") or "").strip()
    name = (fields.get("NAME") or "").strip()
    market = (fields.get("MARKET") or "").strip().upper()

    if action not in ("add", "remove"):
        print(f"❌ 無法辨識的 ACTION：`{fields.get('ACTION', '(空白)')}`（必須是 add 或 remove）", file=sys.stderr)
        sys.exit(2)
    if not symbol:
        print("❌ 缺少 SYMBOL 欄位，請確認申請表單有填寫股票代碼。", file=sys.stderr)
        sys.exit(2)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    for m in VALID_MARKETS:
        config.setdefault("stocks", {}).setdefault(m, [])

    if action == "add":
        if market not in VALID_MARKETS:
            print(f"❌ MARKET 必須是 TW 或 US（收到：`{fields.get('MARKET', '(空白)')}`）", file=sys.stderr)
            sys.exit(2)
        if not name:
            print("❌ 缺少 NAME 欄位，請確認申請表單有填寫股票名稱。", file=sys.stderr)
            sys.exit(2)

        already_tracked = any(
            s.get("symbol", "").upper() == symbol.upper()
            for mkt in VALID_MARKETS
            for s in config["stocks"][mkt]
        )
        if already_tracked:
            print(f"⚠️ {symbol} 已經在監控清單中，未重複新增。", file=sys.stderr)
            sys.exit(2)

        config["stocks"][market].append({"symbol": symbol, "name": name, "market": market})
        message = f"✅ 已新增監控股票：**{symbol}（{name}）**，市場：{market}。下一次資料更新完成後即可在儀表板看到（通常數分鐘內）。"

    else:  # remove
        removed_from = None
        for mkt in VALID_MARKETS:
            before = len(config["stocks"][mkt])
            config["stocks"][mkt] = [
                s for s in config["stocks"][mkt] if s.get("symbol", "").upper() != symbol.upper()
            ]
            if len(config["stocks"][mkt]) < before:
                removed_from = mkt

        if removed_from is None:
            print(f"⚠️ 監控清單中找不到 {symbol}，未進行任何變更。", file=sys.stderr)
            sys.exit(2)

        message = f"✅ 已從監控清單移除：**{symbol}**。"

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(message)
    sys.exit(0)


if __name__ == "__main__":
    main()
