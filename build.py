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
    """공공데이터포털에서 전국 약국 전체 데이터를 페이지네이션으로 수집"""
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
        try:
            res = requests.get(url, params=params, timeout=20)
            res.raise_for_status()
            data = res.json()
            body = data.get("response", {}).get("body", {})

            if page_no == 1:
                total_count = int(body.get("totalCount", 0))
                total_pages = math.ceil(total_count / num_of_rows)
                print(f"[정보] 총 약국 수: {total_count}개 / 총 페이지: {total_pages}페이지")

            items_wrapper = body.get("items")
            if not items_wrapper or not isinstance(items_wrapper, dict):
                break

            items = items_wrapper.get("item", [])
            if isinstance(items, dict):
                items = [items]

            all_items.extend(items)
            print(f"  - {page_no}/{total_pages} 페이지 수집 완료 (누적 {len(all_items)}개)")
            page_no += 1
            time.sleep(0.2)
        except Exception as e:
            print(f"[경고] {page_no}페이지 수집 중 오류 발생: {e}")
            break

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

        <!-- 동네/약국명 실시간 검색창 -->
        <div class="mt-4">
            <input type="text" id="searchInput" placeholder="동네 이름이나 약국 이름을 검색하세요 (예: 운정, 금촌)"
                class="w-full px-4 py-3 rounded-xl border border-gray-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
        </div>

        <!-- 상단 애드센스 슬롯 -->
        <div class="my-5 bg-gray-100 border border-dashed border-gray-300 rounded-lg p-4 text-center text-xs text-gray-400">
            광고 영역 (Google AdSense)
        </div>

        <section id="cardList" class="grid gap-4">
            {cards_html}
        </section>

        <!-- 하단 애드센스 슬롯 -->
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
        sido
