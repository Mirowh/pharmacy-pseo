import os
import json
import urllib.parse
import requests
from datetime import datetime

# ==========================================
# 1. 설정 (환경변수에 API 키가 없으면 샘플 데이터로 자동 테스트)
# ==========================================
API_KEY = os.environ.get("DATA_GO_KR_API_KEY", "")
SITE_URL = "https://your-site-name.netlify.app"  # 나중에 본인 도메인/Netlify 주소로 변경
DIST_DIR = "dist"
AREA_DIR = os.path.join(DIST_DIR, "area")

# 테스트용 샘플 데이터 (API 키 없이 바로 결과물 확인 가능)
SAMPLE_DATA = [
    {
        "dutyName": "운정365열린약국",
        "dutyAddr": "경기도 파주시 와동동 123-4 1층",
        "dutyTel1": "031-941-0001",
        "dutyTime1s": "0900", "dutyTime1c": "2300", # 월
        "dutyTime6s": "0900", "dutyTime6c": "2200", # 토
        "dutyTime7s": "1000", "dutyTime7c": "2100", # 일
        "dutyTime8s": "1000", "dutyTime8c": "2100", # 공휴일
    },
    {
        "dutyName": "금촌야간온누리약국",
        "dutyAddr": "경기도 파주시 금촌동 456-7",
        "dutyTel1": "031-942-0002",
        "dutyTime1s": "0900", "dutyTime1c": "2200",
        "dutyTime6s": "0900", "dutyTime6c": "1800",
        "dutyTime7s": "", "dutyTime7c": "",
        "dutyTime8s": "1000", "dutyTime8c": "1800",
    },
    {
        "dutyName": "강남심야중앙약국",
        "dutyAddr": "서울특별시 강남구 역삼동 789-1",
        "dutyTel1": "02-555-0003",
        "dutyTime1s": "0900", "dutyTime1c": "2400",
        "dutyTime6s": "0900", "dutyTime6c": "2400",
        "dutyTime7s": "1000", "dutyTime7c": "2300",
        "dutyTime8s": "1000", "dutyTime8c": "2300",
    }
]

def fetch_pharmacies():
    """공공데이터포털에서 전국 약국 데이터 수집"""
    if not API_KEY:
        print("[안내] API 키가 없어 샘플 데이터로 사이트를 생성합니다.")
        return SAMPLE_DATA

    url = "http://apis.data.go.kr/B552657/ErmctInsttInfoInqireService/getParmacyFullDown"
    params = {
        "serviceKey": urllib.parse.unquote(API_KEY),
        "pageNo": "1",
        "numOfRows": "1000", # 실제 운영 시 반복문으로 전체 페이지 수집
        "_type": "json"
    }
    try:
        res = requests.get(url, params=params, timeout=15)
        items = res.json()["response"]["body"]["items"]["item"]
        return items if isinstance(items, list) else [items]
    except Exception as e:
        print(f"[오류] API 호출 실패, 샘플 데이터로 대체합니다: {e}")
        return SAMPLE_DATA

def format_time(start, end):
    if not start or not end:
        return "휴무"
    s = str(start).zfill(4)
    e = str(end).zfill(4)
    return f"{s[:2]}:{s[2:]} ~ {e[:2]}:{e[2:]}"

def is_night_or_weekend(item):
    """야간(20시 이후) 또는 일요일/공휴일 운영 여부 필터링"""
    mon_close = int(item.get("dutyTime1c") or 0)
    sun_open = bool(item.get("dutyTime7s"))
    hol_open = bool(item.get("dutyTime8s"))
    return mon_close >= 2000 or sun_open or hol_open

def make_slug(sido, sigungu):
    """URL용 안전한 파일명 생성"""
    return urllib.parse.quote(f"{sido}-{sigungu}")

def render_area_page(sido, sigungu, items, today_str):
    title = f"{sido} {sigungu} 야간·주말·일요일 문 여는 약국 목록 ({today_str[:4]}년 최신)"
    desc = f"{sido} {sigungu} 지역에서 평일 야간, 토요일, 일요일 및 공휴일에 문 여는 약국 전화번호와 영업시간을 한눈에 확인하세요."

    cards_html = ""
    for p in items:
        name = p.get("dutyName", "이름 없음")
        addr = p.get("dutyAddr", "")
        tel = p.get("dutyTel1", "")
        mon = format_time(p.get("dutyTime1s"), p.get("dutyTime1c"))
        sat = format_time(p.get("dutyTime6s"), p.get("dutyTime6c"))
        sun = format_time(p.get("dutyTime7s"), p.get("dutyTime7c"))
        hol = format_time(p.get("dutyTime8s"), p.get("dutyTime8c"))

        cards_html += f"""
        <article class="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition">
            <div class="flex justify-between items-start gap-2">
                <h2 class="text-lg font-bold text-gray-900">{name}</h2>
                <a href="tel:{tel}" class="shrink-0 bg-blue-600 text-white text-xs font-semibold px-3 py-1.5 rounded-lg hover:bg-blue-700">전화하기</a>
            </div>
            <p class="text-sm text-gray-600 mt-1">{addr}</p>
            <p class="text-sm font-medium text-blue-700 mt-1">{tel}</p>
            <div class="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-gray-100 text-xs text-gray-700">
                <div><span class="font-semibold text-gray-900">평일:</span> {mon}</div>
                <div><span class="font-semibold text-gray-900">토요일:</span> {sat}</div>
                <div><span class="font-semibold text-red-600">일요일:</span> {sun}</div>
                <div><span class="font-semibold text-red-600">공휴일:</span> {hol}</div>
            </div>
        </article>
        """

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="{desc}">
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- 구글 애드센스 코드 삽입 위치 -->
</head>
<body class="bg-gray-50 text-gray-900">
    <header class="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div class="max-w-3xl mx-auto px-4 py-4 flex justify-between items-center">
            <a href="../index.html" class="font-extrabold text-lg text-blue-700">365 야간·주말 약국찾기</a>
            <span class="text-xs text-gray-500">업데이트: {today_str}</span>
        </div>
    </header>

    <main class="max-w-3xl mx-auto px-4 py-6">
        <h1 class="text-2xl font-extrabold text-gray-900 leading-tight">{sido} {sigungu} 야간·주말 약국</h1>
        <p class="text-sm text-gray-600 mt-2">총 <strong>{len(items)}곳</strong>의 야간·일요일·공휴일 운영 약국이 확인되었습니다. 방문 전 전화 확인을 권장합니다.</p>

        <!-- 상단 애드센스 슬롯 -->
        <div class="my-5 bg-gray-100 border border-dashed border-gray-300 rounded-lg p-4 text-center text-xs text-gray-400">
            광고 영역 (Google AdSense)
        </div>

        <section class="grid gap-4">
            {cards_html}
        </section>

        <!-- 하단 애드센스 슬롯 -->
        <div class="my-6 bg-gray-100 border border-dashed border-gray-300 rounded-lg p-4 text-center text-xs text-gray-400">
            광고 영역 (Google AdSense)
        </div>
    </main>

    <footer class="max-w-3xl mx-auto px-4 py-8 text-center text-xs text-gray-400 border-t border-gray-200">
        데이터 출처: 공공데이터포털(국립중앙의료원) · 매일 자동 갱신됩니다.
    </footer>
</body>
</html>"""

def build():
    os.makedirs(AREA_DIR, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    raw_items = fetch_pharmacies()

    # 시/도 + 시/군/구 기준으로 그룹핑
    grouped = {}
    for item in raw_items:
        if not is_night_or_weekend(item):
            continue
        addr_parts = item.get("dutyAddr", "").split()
        if len(addr_parts) < 2:
            continue
        sido, sigungu = addr_parts[0], addr_parts[1]
        grouped.setdefault((sido, sigungu), []).append(item)

    links_html = ""
    sitemap_urls = [f"{SITE_URL}/"]

    for (sido, sigungu), items in sorted(grouped.items()):
        filename = f"{sido}-{sigungu}.html"
        filepath = os.path.join(AREA_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(render_area_page(sido, sigungu, items, today_str))

        encoded_name = urllib.parse.quote(filename)
        links_html += f'<a href="area/{encoded_name}" class="block bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-500 transition"><div class="font-bold text-gray-900">{sido} {sigungu}</div><div class="text-xs text-gray-500 mt-1">운영 약국 {len(items)}곳</div></a>\n'
        sitemap_urls.append(f"{SITE_URL}/area/{encoded_name}")

    # 메인 index.html 생성
    index_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>전국 야간·주말·공휴일 문 여는 약국 실시간 찾기</title>
    <meta name="description" content="전국 시군구별 평일 야간, 토요일, 일요일, 공휴일에 문 여는 약국 영업시간과 전화번호를 확인하세요.">
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 text-gray-900">
    <main class="max-w-3xl mx-auto px-4 py-10">
        <h1 class="text-3xl font-extrabold text-blue-700">365 야간·주말 약국찾기</h1>
        <p class="text-sm text-gray-600 mt-2">지역을 선택하면 해당 지역의 야간·일요일·공휴일 운영 약국을 바로 볼 수 있습니다. (업데이트: {today_str})</p>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-6">
            {links_html}
        </div>
    </main>
</body>
</html>"""

    with open(os.path.join(DIST_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    # sitemap.xml 생성 (구글·네이버 자동 수집용)
    sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in sitemap_urls:
        sitemap_xml += f"  <url><loc>{u}</loc><lastmod>{today_str}</lastmod></url>\n"
    sitemap_xml += "</urlset>"
    with open(os.path.join(DIST_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap_xml)

    # robots.txt 생성
    with open(os.path.join(DIST_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")

    print(f"[완료] 총 {len(grouped)}개 지역 페이지 및 sitemap.xml 생성 완료! (폴더: {DIST_DIR}/)")

if __name__ == "__main__":
    build()
