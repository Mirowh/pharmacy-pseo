import os
import math
import time
import urllib.parse
import requests
from datetime import datetime

# ==========================================
# 1. 기본 설정
# ==========================================
API_KEY = os.environ.get("DATA_GO_KR_API_KEY", "")
SITE_URL = "https://delicate-longma-2e8367.netlify.app"
DIST_DIR = "dist"
AREA_DIR = os.path.join(DIST_DIR, "area")

def fetch_all_pharmacies():
    """공공데이터포털에서 전국 약국 전체 데이터를 수집 (실패 시 최대 3회 재시도)"""
    if not API_KEY:
        raise ValueError("DATA_GO_KR_API_KEY 환경변수가 설정되지 않았습니다.")

    url = "http://apis.data.go.kr/B552657/ErmctInsttInfoInqireService/getParmacyFullDown"
    decoded_key = urllib.parse.unquote(API_KEY)
    all_items = []
    num_of_rows = 1000
    page_no = 1
    total_pages = 1

    print("[시작] 전국 약국 데이터 수집을 시작합니다...")
    while page_no <= total_pages:
        params = {
            "serviceKey": decoded_key,
            "pageNo": str(page_no),
            "numOfRows": str(num_of_rows),
            "_type": "json"
        }
        success = False
        for attempt in range(1, 4):
            try:
                res = requests.get(url, params=params, timeout=30)
                res.raise_for_status()
                data = res.json()
                body = data.get("response", {}).get("body", {})

                if page_no == 1:
                    total_count = int(body.get("totalCount", 0))
                    total_pages = math.ceil(total_count / num_of_rows)
                    print(f"[정보] 총 약국 수: {total_count}개 / 총 페이지: {total_pages}페이지")

                items_wrapper = body.get("items")
                if not items_wrapper or not isinstance(items_wrapper, dict):
                    success = True
                    break

                items = items_wrapper.get("item", [])
                if isinstance(items, dict):
                    items = [items]

                all_items.extend(items)
                print(f"  - {page_no}/{total_pages} 페이지 수집 완료 (누적 {len(all_items)}개)")
                success = True
                break
            except Exception as e:
                print(f"[재시도 {attempt}/3] {page_no}페이지 오류: {e}")
                time.sleep(2)

        if not success:
            print(f"[건너뜀] {page_no}페이지 수집 실패, 다음 페이지로 진행합니다.")
        page_no += 1
        time.sleep(0.2)

    return all_items

def format_time(start, end):
    if not start or not end:
        return "휴무"
    s = str(start).zfill(4)
    e = str(end).zfill(4)
    return f"{s[:2]}:{s[2:]} ~ {e[:2]}:{e[2:]}"

def is_night_or_weekend(item):
    """평일 야간(20시 이후 종료) 또는 일요일/공휴일 운영 약국 필터링"""
    try:
        mon_close = int(item.get("dutyTime1c") or 0)
    except ValueError:
        mon_close = 0
    sun_open = bool(item.get("dutyTime7s"))
    hol_open = bool(item.get("dutyTime8s"))
    return mon_close >= 2000 or sun_open or hol_open

def render_area_page(sido, sigungu, items, today_str):
    title = f"{sido} {sigungu} 야간·주말·일요일 문 여는 약국 ({today_str[:4]}년 최신)"
    desc = f"{sido} {sigungu} 지역 평일 야간, 토요일, 일요일 및 공휴일 운영 약국 {len(items)}곳의 영업시간, 전화번호, 길찾기 정보를 확인하세요."

    cards_html = ""
    for p in items:
        name = p.get("dutyName", "이름 없음")
        addr = p.get("dutyAddr", "")
        tel = p.get("dutyTel1", "")
        mon = format_time(p.get("dutyTime1s"), p.get("dutyTime1c"))
        sat = format_time(p.get("dutyTime6s"), p.get("dutyTime6c"))
        sun = format_time(p.get("dutyTime7s"), p.get("dutyTime7c"))
        hol = format_time(p.get("dutyTime8s"), p.get("dutyTime8c"))

        map_query = urllib.parse.quote(f"{sido} {sigungu} {name}")
        map_url = f"https://map.kakao.com/link/search/{map_query}"

        badges = ""
        if sun != "휴무":
            badges += '<span class="bg-red-100 text-red-700 text-[11px] font-bold px-2 py-0.5 rounded">일요일 운영</span> '
        if hol != "휴무":
            badges += '<span class="bg-orange-100 text-orange-700 text-[11px] font-bold px-2 py-0.5 rounded">공휴일 운영</span>'

        cards_html += f"""
        <article class="pharmacy-card bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition" data-search="{name} {addr}">
            <div class="flex justify-between items-start gap-2">
                <div>
                    <div class="mb-1">{badges}</div>
                    <h2 class="text-lg font-bold text-gray-900">{name}</h2>
                </div>
                <div class="flex gap-1.5 shrink-0">
                    <a href="{map_url}" target="_blank" rel="noopener" class="bg-yellow-400 text-gray-900 text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-yellow-500">길찾기</a>
                    <a href="tel:{tel}" class="bg-blue-600 text-white text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-blue-700">전화</a>
                </div>
            </div>
            <p class="text-sm text-gray-600 mt-1.5">{addr}</p>
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
            <a href="../index.html" class="font-extrabold text-lg text-blue-700">← 365 야간·주말 약국찾기</a>
            <span class="text-xs text-gray-500">업데이트: {today_str}</span>
        </div>
    </header>

    <main class="max-w-3xl mx-auto px-4 py-6">
        <h1 class="text-2xl font-extrabold text-gray-900 leading-tight">{sido} {sigungu} 야간·주말 약국</h1>
        <p class="text-sm text-gray-600 mt-2">총 <strong>{len(items)}곳</strong>의 야간·일요일·공휴일 운영 약국이 확인되었습니다. 방문 전 전화 확인을 권장합니다.</p>

        <div class="mt-4">
            <input type="text" id="searchInput" placeholder="동네 이름이나 약국 이름을 검색하세요 (예: 운정, 금촌)"
                class="w-full px-4 py-3 rounded-xl border border-gray-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
        </div>

        <div class="my-5 bg-gray-100 border border-dashed border-gray-300 rounded-lg p-4 text-center text-xs text-gray-400">
            광고 영역 (Google AdSense)
        </div>

        <section id="cardList" class="grid gap-4">
            {cards_html}
        </section>

        <div class="my-6 bg-gray-100 border border-dashed border-gray-300 rounded-lg p-4 text-center text-xs text-gray-400">
            광고 영역 (Google AdSense)
        </div>
    </main>

    <footer class="max-w-3xl mx-auto px-4 py-8 text-center text-xs text-gray-400 border-t border-gray-200">
        데이터 출처: 공공데이터포털(국립중앙의료원) · 매일 새벽 자동 갱신됩니다.
    </footer>

    <script>
        document.getElementById('searchInput').addEventListener('input', function(e) {{
            const kw = e.target.value.trim().toLowerCase();
            document.querySelectorAll('.pharmacy-card').forEach(card => {{
                const text = card.getAttribute('data-search').toLowerCase();
                card.style.display = text.includes(kw) ? '' : 'none';
            }});
        }});
    </script>
</body>
</html>"""

def build():
    os.makedirs(AREA_DIR, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    raw_items = fetch_all_pharmacies()

    grouped = {}
    for item in raw_items:
        if not is_night_or_weekend(item):
            continue
        addr_parts = str(item.get("dutyAddr", "")).split()
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
        links_html += f'<a href="area/{encoded_name}" class="area-card block bg-white border border-gray-200 rounded-xl p-4 hover:border-blue-500 hover:shadow-sm transition" data-area="{sido} {sigungu}"><div class="font-bold text-gray-900">{sido} {sigungu}</div><div class="text-xs text-gray-500 mt-1">운영 약국 {len(items)}곳</div></a>\n'
        sitemap_urls.append(f"{SITE_URL}/area/{encoded_name}")

    index_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>전국 야간·주말·공휴일 문 여는 약국 실시간 찾기</title>
    <meta name="description" content="전국 시군구별 평일 야간, 토요일, 일요일, 공휴일에 문 여는 약국 영업시간과 전화번호를 한눈에 확인하세요.">
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 text-gray-900">
    <main class="max-w-4xl mx-auto px-4 py-10">
        <h1 class="text-3xl font-extrabold text-blue-700">365 야간·주말 약국찾기</h1>
        <p class="text-sm text-gray-600 mt-2">전국 <strong>{len(grouped)}개</strong> 지역의 야간·일요일·공휴일 운영 약국을 매일 자동 업데이트합니다. (업데이트: {today_str})</p>

        <div class="mt-5">
            <input type="text" id="areaSearch" placeholder="지역명을 검색하세요 (예: 파주, 강남, 부산, 일산)"
                class="w-full px-4 py-3.5 rounded-xl border border-gray-300 bg-white text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
        </div>

        <div id="areaGrid" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 mt-6">
            {links_html}
        </div>
    </main>

    <footer class="max-w-4xl mx-auto px-4 py-8 text-center text-xs text-gray-400">
        데이터 출처: 공공데이터포털(국립중앙의료원) · 매일 새벽 자동 갱신
    </footer>

    <script>
        document.getElementById('areaSearch').addEventListener('input', function(e) {{
            const kw = e.target.value.trim().toLowerCase();
            document.querySelectorAll('.area-card').forEach(card => {{
                const text = card.getAttribute('data-area').toLowerCase();
                card.style.display = text.includes(kw) ? '' : 'none';
            }});
        }});
    </script>
</body>
</html>"""

    with open(os.path.join(DIST_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in sitemap_urls:
        sitemap_xml += f"  <url><loc>{u}</loc><lastmod>{today_str}</lastmod></url>\n"
    sitemap_xml += "</urlset>"
    with open(os.path.join(DIST_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap_xml)

    with open(os.path.join(DIST_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")

    print(f"[완료] 전국 {len(grouped)}개 지역 페이지 및 sitemap.xml 생성 완료!")

if __name__ == "__main__":
    build()
