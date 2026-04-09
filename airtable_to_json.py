"""
airtable_to_json.py
Airtable의 works 테이블을 읽어서 kugak.json을 생성합니다.
GitHub Actions에서 자동 실행됩니다.
"""

import os, json, re, requests
from collections import Counter, defaultdict

# ── 설정 ──────────────────────────────────────────────────
AIRTABLE_TOKEN  = os.environ["AIRTABLE_TOKEN"]
AIRTABLE_BASE_ID = os.environ["AIRTABLE_BASE_ID"]
TABLE_NAME      = "works"          # Airtable 테이블 이름
OUT_FILE        = "kugak.json"     # 출력 파일명

# Airtable 컬럼명 → JSON 키 매핑
# Airtable에서 컬럼 이름을 바꿨다면 왼쪽(Airtable 컬럼명)을 맞게 수정하세요
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


def fetch_all_records():
    """Airtable에서 전체 레코드를 페이지 단위로 가져옵니다."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    records, offset = [], None

    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        records.extend(data.get("records", []))
        offset = data.get("offset")
        print(f"  불러온 레코드: {len(records)}개...", end="\r")
        if not offset:
            break

    print(f"\n총 {len(records):,}개 레코드 로드 완료")
    return records


def records_to_works(records):
    """Airtable 레코드를 works 딕셔너리 목록으로 변환합니다."""
    all_json_keys = list(FIELD_MAP.values())
    works = []
    for rec in records:
        fields = rec.get("fields", {})
        w = {v: str(fields.get(k, "")).strip() for k, v in FIELD_MAP.items()}
        # 매핑에 없는 키도 빈값으로 보장
        for key in all_json_keys:
            w.setdefault(key, "")
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
            if ins in w["pp"]:
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
    print("Airtable에서 데이터 불러오는 중...")
    records = fetch_all_records()

    print("works 변환 중...")
    works = records_to_works(records)

    print("통계 계산 중...")
    stats = calc_stats(works)

    out = {"works": works, "stats": stats}
    json_str = json.dumps(out, ensure_ascii=False, separators=(",", ":"))

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(json_str)

    size_kb = len(json_str) / 1024
    print(f"\n완료: {OUT_FILE} 저장 ({size_kb:.1f} KB, {len(works):,}개 작품)")
    print(f"  해설 있음: {sum(1 for w in works if w['cm']):,}개")
    print(f"  note_02 있음: {sum(1 for w in works if w['n2']):,}개")


if __name__ == "__main__":
    main()
