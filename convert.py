"""
convert.py  —  CSV → kugak.json 변환 스크립트
사용법: python convert.py
같은 폴더에 CSV 파일과 이 스크립트를 두고 실행하면 kugak.json이 생성됩니다.
"""

import csv, json, re, os
from collections import Counter, defaultdict

# ── 설정 ──────────────────────────────────────────────
CSV_FILE = "편집중_Chart_입력용_xlsx_-_wp_wct3_titleinput__2_.csv"   # CSV 파일명
OUT_FILE = "kugak.json"                                               # 출력 파일명
# ─────────────────────────────────────────────────────

def safe(r, k):
    return (r.get(k) or "").strip()

def main():
    if not os.path.exists(CSV_FILE):
        print(f"오류: '{CSV_FILE}' 파일을 찾을 수 없습니다.")
        print("CSV 파일명을 확인하고 스크립트 상단의 CSV_FILE 변수를 수정해주세요.")
        return

    print(f"'{CSV_FILE}' 읽는 중...")
    rows = []
    with open(CSV_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rows.append(row)
    print(f"  총 {len(rows):,}행 읽음")

    # 작품 데이터
    works = []
    for r in rows:
        works.append({
            "t":  safe(r, "title"),
            "f1": safe(r, "form1"),
            "f2": safe(r, "form2"),
            "f3": safe(r, "form3"),
            "c":  safe(r, "composer"),
            "d":  safe(r, "perform_date"),
            "n":  safe(r, "perform_name"),
            "p":  safe(r, "perform_place"),
        })

    # 통계
    genres    = Counter(w["f1"] for w in works if w["f1"] and len(w["f1"]) < 20)
    forms     = Counter(w["f2"] for w in works if w["f2"])
    composers = Counter(w["c"]  for w in works if w["c"] and w["c"] not in ["민요","전래","작자미상"])

    year_counts  = defaultdict(int)
    month_counts = defaultdict(int)
    heatmap      = defaultdict(lambda: defaultdict(int))

    for w in works:
        ym = re.search(r"(1[89]\d{2}|20[012]\d)", w["d"])
        if ym:
            y = int(ym.group(1))
            year_counts[y] += 1
            mo = re.search(r"(1[89]\d{2}|20[012]\d)[.\-/](\d{1,2})", w["d"])
            if mo:
                m = int(mo.group(2))
                if 1 <= m <= 12:
                    month_counts[m] += 1
                    heatmap[y][m]   += 1

    instr_list = ["가야금","대금","거문고","해금","피리","아쟁","장구","소금","양금","생황","타악","첼로","피아노","기타","바이올린"]
    instr_counts = Counter()
    for w in works:
        for ins in instr_list:
            if ins in w["p"]:
                instr_counts[ins] += 1

    stats = {
        "total":          len(works),
        "genres":         dict(genres.most_common(6)),
        "forms":          dict(forms.most_common(12)),
        "composers_top":  composers.most_common(20),
        "year_counts":    {str(k): v for k, v in sorted(year_counts.items())  if k >= 1950},
        "month_counts":   {str(k): v for k, v in sorted(month_counts.items())},
        "heatmap":        {str(y): {str(m): heatmap[y][m] for m in range(1,13)}
                           for y in sorted(heatmap) if y >= 1970},
        "instr":          dict(instr_counts.most_common()),
    }

    out = {"works": works, "stats": stats}
    json_str = json.dumps(out, ensure_ascii=False, separators=(",", ":"))

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(json_str)

    size_kb = len(json_str) / 1024
    print(f"완료! '{OUT_FILE}' 저장됨 ({size_kb:.1f} KB, {len(works):,}개 작품)")
    print(f"  장르: {dict(genres.most_common(3))}")
    print(f"  형식 수: {len(forms)}")
    print(f"  작곡가 TOP3: {composers.most_common(3)}")

if __name__ == "__main__":
    main()
