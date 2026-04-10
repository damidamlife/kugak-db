"""
sheets_to_db.py
Google Sheets CSV → kugak.json + kugak.db (SQLite) 동시 생성
GitHub Actions에서 자동 실행됩니다.
"""

import os, io, json, re, csv, sqlite3, requests
from collections import defaultdict

# ── 설정 ──────────────────────────────────────────────────
SHEETS_CSV_URL = os.environ["SHEETS_CSV_URL"]
JSON_FILE      = "kugak.json"
DB_FILE        = "kugak.db"

FIELD_MAP = {
    "title":        "t",
    "form1":        "f1",
    "form2":        "f2",
    "form3":        "f3",
    "composer":     "c",
    "arrangement":  "ar",
    "lyric":        "ly",
    "constructure": "cs",
    "perform_date": "d",
    "perform_name": "n",
    "perform_place":"p",
    "perform_play": "pp",
    "note":         "nt",
    "commentary":   "cm",
    "add_note":     "an",
    "note_02":      "n2",
}
# ──────────────────────────────────────────────────────────


def fetch_csv():
    print("Google Sheets CSV 다운로드 중...")
    resp = requests.get(SHEETS_CSV_URL, timeout=60)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def parse_csv(text):
    reader = csv.DictReader(io.StringIO(text))
    all_keys = list(FIELD_MAP.values())
    works = []
    for row in reader:
        w = {v: (row.get(k) or "").strip() for k, v in FIELD_MAP.items()}
        for key in all_keys:
            w.setdefault(key, "")
        if w.get("t"):      # 제목 없는 빈 행 제거
            works.append(w)
    return works


def calc_stats(works):
    genres, forms, composers_c = {}, {}, {}
    year_c, month_c = defaultdict(int), defaultdict(int)
    heatmap = defaultdict(lambda: defaultdict(int))
    instr_c = {}
    INSTR = ["가야금","대금","거문고","해금","피리","아쟁","장구","소금",
             "양금","생황","타악","첼로","피아노","기타","바이올린"]

    for w in works:
        if w["f1"] and len(w["f1"]) < 20:
            genres[w["f1"]] = genres.get(w["f1"], 0) + 1
        if w["f2"]:
            forms[w["f2"]] = forms.get(w["f2"], 0) + 1
        if w["c"] and w["c"] not in ["민요","전래","작자미상"]:
            composers_c[w["c"]] = composers_c.get(w["c"], 0) + 1
        for ins in INSTR:
            if ins in (w["pp"] or ""):
                instr_c[ins] = instr_c.get(ins, 0) + 1
        ym = re.search(r"(1[89]\d{2}|20[012]\d)", w["d"])
        if ym:
            y = int(ym.group(1))
            year_c[y] += 1
            mo = re.search(r"(1[89]\d{2}|20[012]\d)[.\-/](\d{1,2})", w["d"])
            if mo:
                m = int(mo.group(2))
                if 1 <= m <= 12:
                    month_c[m] += 1
                    heatmap[y][m] += 1

    hm_full = {
        str(y): {str(m): heatmap[y].get(m, 0) for m in range(1, 13)}
        for y in sorted(heatmap) if y >= 1970
    }
    return {
        "total":         len(works),
        "genres":        dict(sorted(genres.items(), key=lambda x:-x[1])[:6]),
        "forms":         dict(sorted(forms.items(), key=lambda x:-x[1])[:12]),
        "composers_top": sorted(composers_c.items(), key=lambda x:-x[1])[:20],
        "year_counts":   {str(k): v for k, v in sorted(year_c.items()) if k >= 1950},
        "month_counts":  {str(k): v for k, v in sorted(month_c.items())},
        "heatmap":       hm_full,
        "instr":         dict(sorted(instr_c.items(), key=lambda x:-x[1])),
    }


def save_json(works, stats):
    """kugak.json 저장"""
    out = {"works": works, "stats": stats}
    json_str = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        f.write(json_str)
    print(f"  {JSON_FILE} 저장 완료 ({len(json_str)/1024:.1f} KB)")


def save_sqlite(works):
    """kugak.db SQLite 저장"""
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # works 테이블 생성
    cur.execute("""
        CREATE TABLE works (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            title     TEXT,
            genre     TEXT,    -- form1
            form      TEXT,    -- form2
            instrument TEXT,   -- form3
            composer  TEXT,
            arrangement TEXT,
            lyric     TEXT,
            structure TEXT,    -- constructure
            perf_date TEXT,
            perf_name TEXT,
            perf_place TEXT,
            perf_play TEXT,
            note      TEXT,
            commentary TEXT,
            add_note  TEXT,
            note_02   TEXT
        )
    """)

    # 데이터 삽입
    rows = [(
        w["t"], w["f1"], w["f2"], w["f3"], w["c"],
        w["ar"], w["ly"], w["cs"], w["d"], w["n"],
        w["p"], w["pp"], w["nt"], w["cm"], w["an"], w["n2"]
    ) for w in works]

    cur.executemany("""
        INSERT INTO works
        (title,genre,form,instrument,composer,arrangement,lyric,structure,
         perf_date,perf_name,perf_place,perf_play,note,commentary,add_note,note_02)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)

    # 검색 속도를 위한 인덱스
    cur.execute("CREATE INDEX idx_genre    ON works(genre)")
    cur.execute("CREATE INDEX idx_form     ON works(form)")
    cur.execute("CREATE INDEX idx_composer ON works(composer)")
    cur.execute("CREATE INDEX idx_date     ON works(perf_date)")

    # 전문 검색(FTS5) 테이블 — 제목·작곡가·해설을 빠르게 검색
    cur.execute("""
        CREATE VIRTUAL TABLE works_fts USING fts5(
            title, composer, perf_name, commentary, note, note_02,
            content='works', content_rowid='id'
        )
    """)
    cur.execute("""
        INSERT INTO works_fts(rowid, title, composer, perf_name, commentary, note, note_02)
        SELECT id, title, composer, perf_name, commentary, note, note_02 FROM works
    """)

    conn.commit()
    conn.close()

    size_mb = os.path.getsize(DB_FILE) / 1024 / 1024
    print(f"  {DB_FILE} 저장 완료 ({size_mb:.1f} MB, FTS 인덱스 포함)")


def main():
    text  = fetch_csv()
    works = parse_csv(text)
    print(f"  {len(works):,}개 행 파싱 완료")

    print("통계 계산 중...")
    stats = calc_stats(works)

    print("파일 저장 중...")
    save_json(works, stats)
    save_sqlite(works)

    print(f"\n완료!")
    print(f"  작품해설 있음: {sum(1 for w in works if w['cm']):,}개")
    print(f"  note_02 있음:  {sum(1 for w in works if w['n2']):,}개")


if __name__ == "__main__":
    main()
