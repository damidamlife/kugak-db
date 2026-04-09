"""
sheets_to_json.py
Google Sheets의 공개 CSV URL을 읽어 kugak.json을 생성합니다.
GitHub Actions에서 자동 실행됩니다.
"""

import os, io, json, re, csv, requests
from collections import defaultdict

# ── 설정 ──────────────────────────────────────────────────
SHEETS_CSV_URL = os.environ["SHEETS_CSV_URL"]   # GitHub Secret에서 읽음
OUT_FILE       = "kugak.json"
DELIMITER      = "\t"   # 탭 구분자. 쉼표 CSV라면 "," 로 변경

# Google Sheets 컬럼명 → JSON 키 매핑
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
    """Google Sheets 공개 URL에서 CSV를 다운로드합니다."""
    print(f"CSV 다운로드 중...")
    resp = requests.get(SHEETS_CSV_URL, timeout=60)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def parse_csv(text):
    """CSV 텍스트를 파싱해서 works 목록으로 변환합니다."""
    # Google Sheets 게시 URL은 항상 쉼표(,) CSV로 내보냄
    # 원본이 탭이어도 게시하면 쉼표로 변환됨
    reader = csv.DictReader(io.StringIO(text))
    all_json_keys = list(FIELD_MAP.values())
    works = []
    for row in reader:
        w = {}
        for csv_col, json_key in FIELD_MAP.items():
            w[json_key] = (row.get(csv_col) or "").strip()
        # 매핑 누락된 키 보장
        for key in all_json_keys:
            w.setdefault(key, "")
        # 제목이 없는 빈 행 제거
        if w.get("t"):
            works.append(w)
    return works


def calc_stats(works):
    """통계 데이터를 계산합니다."""
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
        "genres":        dict(sorted(genres.items(), key=lambda x: -x[1])[:6]),
        "forms":         dict(sorted(forms.items(), key=lambda x: -x[1])[:12]),
        "composers_top": sorted(composers_c.items(), key=lambda x: -x[1])[:20],
        "year_counts":   {str(k): v for k, v in sorted(year_c.items()) if k >= 1950},
        "month_counts":  {str(k): v for k, v in sorted(month_c.items())},
        "heatmap":       hm_full,
        "instr":         dict(sorted(instr_c.items(), key=lambda x: -x[1])),
    }


def main():
    text = fetch_csv()
    print("파싱 중...")
    works = parse_csv(text)
    print(f"  {len(works):,}개 행 파싱 완료")

    print("통계 계산 중...")
    stats = calc_stats(works)

    out = {"works": works, "stats": stats}
    json_str = json.dumps(out, ensure_ascii=False, separators=(",", ":"))

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(json_str)

    size_kb = len(json_str) / 1024
    print(f"\n완료: {OUT_FILE} ({size_kb:.1f} KB, {len(works):,}개 작품)")
    print(f"  작품해설 있음: {sum(1 for w in works if w['cm']):,}개")
    print(f"  note_02 있음:  {sum(1 for w in works if w['n2']):,}개")


if __name__ == "__main__":
    main()
