"""
StockRadar 演示引擎 - Railway 部署版（含情绪数据）
"""

import asyncio
import json
import time
import random
import websockets
import os
import urllib.request
import urllib.error
from datetime import datetime

# Railway 会提供 PORT 环境变量
WS_PORT = int(os.environ.get('PORT', 8080))

STOCKS = [
    ('000001', '平安银行', ['银行','金融科技','数字货币']),
    ('600519', '贵州茅台', ['白酒','消费','大盘蓝筹']),
    ('300750', '宁德时代', ['锂电池','新能源车','储能']),
    ('688256', '寒武纪', ['AI芯片','人工智能','国产替代']),
    ('002230', '科大讯飞', ['人工智能','AI应用','教育信息化']),
    ('300308', '中际旭创', ['光模块','CPO','算力']),
    ('601360', '三六零', ['网络安全','AI大模型','数据要素']),
    ('300418', '昆仑万维', ['AI大模型','AIGC','游戏']),
    ('002261', '拓维信息', ['算力','华为概念','鸿蒙']),
    ('300339', '润和软件', ['鸿蒙','华为概念','金融科技']),
    ('000977', '浪潮信息', ['服务器','算力','国产替代']),
    ('688111', '金山办公', ['AI办公','信创','SaaS']),
    ('688041', '海光信息', ['AI芯片','国产替代','信创']),
    ('300364', '中文在线', ['AI内容','AIGC','数字版权']),
    ('300624', '万兴科技', ['AIGC','AI应用','SaaS']),
    ('600570', '恒生电子', ['金融科技','金融IT','数据要素']),
    ('002371', '北方华创', ['半导体设备','国产替代','芯片']),
    ('688981', '中芯国际', ['芯片','国产替代','半导体设备']),
    ('300059', '东方财富', ['券商','金融科技','互联网金融']),
    ('601012', '隆基绿能', ['光伏','新能源','HJT']),
    ('002475', '立讯精密', ['苹果产业链','消费电子','MR']),
    ('300760', '迈瑞医疗', ['医疗器械','创新药','大盘蓝筹']),
    ('600036', '招商银行', ['银行','金融科技','大盘蓝筹']),
    ('601318', '中国平安', ['保险','金融科技','大盘蓝筹']),
    ('002594', '比亚迪', ['新能源车','锂电池','智能驾驶']),
    ('300274', '阳光电源', ['光伏','储能','新能源']),
    ('688012', '中微公司', ['半导体设备','国产替代','芯片']),
    ('300033', '同花顺', ['金融科技','AI应用','券商']),
    ('300496', '中科创达', ['智能驾驶','鸿蒙','AI应用']),
    ('002049', '紫光国微', ['芯片','国产替代','军工电子']),
    ('688036', '传音控股', ['消费电子','非洲概念','手机']),
    ('603986', '兆易创新', ['存储芯片','国产替代','芯片']),
    ('300782', '卓胜微', ['射频芯片','消费电子','5G']),
    ('002415', '海康威视', ['安防','人工智能','智慧城市']),
    ('300124', '汇川技术', ['工业自动化','机器人','新能源车']),
    ('688169', '石头科技', ['扫地机器人','消费电子','智能家居']),
    ('300474', '景嘉微', ['GPU','国产替代','军工电子']),
    ('002241', '歌尔股份', ['MR','苹果产业链','消费电子']),
    ('300661', '圣邦股份', ['模拟芯片','芯片','国产替代']),
]

ALERT_TEMPLATES = [
    {'type':'rocket','label':'🚀 火箭发射','cr':(3.5,9.8),'sr':(3.0,8.0)},
    {'type':'dive','label':'🏊 高台跳水','cr':(-8.0,-1.5),'sr':(-7.0,-3.0)},
    {'type':'volume','label':'📊 放量突破','cr':(2.0,7.0),'sr':(1.0,4.0)},
    {'type':'limit-up','label':'🔒 接近涨停','cr':(9.0,9.8),'sr':(2.0,6.0)},
    {'type':'limit-up','label':'🔒 涨停','cr':(9.95,10.02),'sr':(0.5,3.0)},
    {'type':'limit-down','label':'🔒 跌停','cr':(-10.02,-9.95),'sr':(-3.0,-0.5)},
    {'type':'volume','label':'💰 超大单 12350手','cr':(1.0,6.0),'sr':(0.5,3.0)},
    {'type':'volume','label':'💰 超大单 9800手','cr':(0.5,4.0),'sr':(0.3,2.0)},
    {'type':'reversal','label':'🔄 V型反转','cr':(-1.0,3.0),'sr':(2.0,5.0)},
]

NEWS_POOL = [
    '工信部发布人工智能产业发展新规划',
    '机构研报上调目标价至历史新高',
    '公司公告拟10转5派3元',
    '获北向资金连续5日净买入',
    '子公司与英伟达达成战略合作',
    '一季度业绩预增120%-150%',
    '大股东增持500万股',
    '纳入MSCI中国指数成分股',
    '获得国产替代大额订单',
    '央行降准0.5个百分点释放1.2万亿',
    '新能源车补贴延续至年底',
    '人形机器人量产进程加速',
    '低空经济政策密集落地',
    '华为发布新一代昇腾芯片',
    '苹果MR头显销量超预期',
    None, None, None, None,
]

# ── 情绪数据：题材板块 ──
SECTOR_NAMES = [
    '人工智能', 'AI芯片', '算力', '光模块', 'CPO', '机器人',
    '低空经济', '新能源车', '锂电池', '光伏', '储能',
    '半导体设备', '国产替代', '信创', '鸿蒙', '华为概念',
    '数据要素', '数字经济', '网络安全', '金融科技',
    '消费电子', 'MR/VR', '苹果产业链', '军工',
    '医药', '白酒', '银行', '券商', '保险', '房地产',
]

def fetch_eastmoney_indices():
    """从东方财富获取沪深指数实时数据"""
    try:
        url = 'https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&invt=2&fields=f12,f14,f2,f3&secids=1.000001,0.399001,1.000300'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://quote.eastmoney.com/'
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            diff = data.get('data', {}).get('diff', [])
            indices = []
            for item in diff:
                indices.append({
                    'name': item.get('f14', ''),
                    'price': item.get('f2', 0),
                    'change': item.get('f3', 0),
                })
            return indices
    except Exception as e:
        print(f"[情绪] 获取指数失败: {e}")
        return None

def fetch_eastmoney_breadth():
    """从东方财富获取涨跌家数（市场宽度）"""
    try:
        url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=1&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f3'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://quote.eastmoney.com/'
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            total = data.get('data', {}).get('total', 0)
            return total
    except Exception as e:
        print(f"[情绪] 获取宽度失败: {e}")
        return None

def fetch_stock_klines(code, days=60):
    """从东方财富获取个股日K线数据"""
    try:
        market = '1' if code.startswith('6') or code.startswith('9') else '0'
        secid = f"{market}.{code}"
        url = (f'https://push2his.eastmoney.com/api/qt/stock/kline/get?'
               f'secid={secid}&fields1=f1,f2,f3,f4,f5,f6'
               f'&fields2=f51,f52,f53,f54,f55,f56,f57'
               f'&klt=101&fqt=1&lmt={days}&end=20500101&_={int(time.time()*1000)}')
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://quote.eastmoney.com/'
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            kline_strs = data.get('data', {}).get('klines', [])
            result = []
            for ks in kline_strs:
                parts = ks.split(',')
                if len(parts) >= 7:
                    result.append({
                        'date': parts[0],
                        'open': float(parts[1]),
                        'close': float(parts[2]),
                        'high': float(parts[3]),
                        'low': float(parts[4]),
                        'volume': float(parts[5]),
                        'amount': float(parts[6]),
                    })
            return result
    except Exception as e:
        print(f"[K线] 获取 {code} 失败: {e}")
        # 降级：生成模拟K线
        result = []
        base = random.uniform(10, 200)
        for i in range(days):
            o = base + random.uniform(-2, 2)
            c = o + random.uniform(-3, 3)
            h = max(o, c) + random.uniform(0, 2)
            l = min(o, c) - random.uniform(0, 2)
            result.append({
                'date': f"2026-{(i//30+1):02d}-{(i%30+1):02d}",
                'open': round(o, 2), 'close': round(c, 2),
                'high': round(h, 2), 'low': round(l, 2),
                'volume': round(random.uniform(1e6, 1e8), 0),
                'amount': round(random.uniform(1e7, 1e9), 0),
            })
            base = c
        return result

def gen_sentiment_data():
    """生成情绪面板数据（实时指数 + 模拟板块数据）"""
    # 1. 尝试获取真实指数数据
    indices = fetch_eastmoney_indices()
    if not indices:
        # 降级：模拟数据
        indices = [
            {'name': '上证指数', 'price': round(3250 + random.uniform(-50, 50), 2), 'change': round(random.uniform(-2, 2), 2)},
            {'name': '深证成指', 'price': round(10200 + random.uniform(-200, 200), 2), 'change': round(random.uniform(-2.5, 2.5), 2)},
            {'name': '沪深300', 'price': round(3800 + random.uniform(-60, 60), 2), 'change': round(random.uniform(-2, 2), 2)},
        ]

    # 2. 市场宽度（模拟）
    up_count = random.randint(800, 3500)
    down_count = random.randint(800, 3500)
    flat_count = random.randint(50, 200)
    total = up_count + down_count + flat_count
    breadth = {
        'up': up_count,
        'down': down_count,
        'flat': flat_count,
        'total': total,
        'ratio': round(up_count / total * 100, 1),
        'limit_up': random.randint(10, 80),
        'limit_down': random.randint(0, 20),
    }

    # 3. 题材涨停排名
    sectors = []
    chosen = random.sample(SECTOR_NAMES, min(10, len(SECTOR_NAMES)))
    for i, name in enumerate(chosen):
        sectors.append({
            'name': name,
            'limit_up_count': random.randint(1, 15) if i < 5 else random.randint(0, 5),
            'change': round(random.uniform(-3, 8), 2),
            'amount': round(random.uniform(50, 800), 1),
        })
    sectors.sort(key=lambda x: x['limit_up_count'], reverse=True)

    # 4. 近7日板块热力
    history = []
    today = datetime.now()
    for day_offset in range(6, -1, -1):
        day_sectors = []
        for name in random.sample(SECTOR_NAMES, 8):
            day_sectors.append({
                'name': name,
                'change': round(random.uniform(-5, 8), 2),
            })
        day_sectors.sort(key=lambda x: x['change'], reverse=True)
        history.append({
            'date': f"{today.month}-{today.day - day_offset}",
            'sectors': day_sectors[:5],
        })

    # 5. 上证K线（模拟20日）
    sh_klines = []
    base = 3200
    for i in range(20):
        o = base + random.uniform(-10, 10)
        c = o + random.uniform(-30, 30)
        h = max(o, c) + random.uniform(0, 15)
        l = min(o, c) - random.uniform(0, 15)
        sh_klines.append({'open': round(o,2), 'close': round(c,2), 'high': round(h,2), 'low': round(l,2)})
        base = c

    return {
        'indices': indices,
        'breadth': breadth,
        'sectors': sectors,
        'history': history,
        'sh_klines': sh_klines,
    }


def gen_alert(offset):
    code, name, concepts = random.choice(STOCKS)
    tmpl = random.choice(ALERT_TEMPLATES)
    change = round(random.uniform(*tmpl['cr']), 2)
    speed = round(random.uniform(*tmpl['sr']), 2)
    amount = round(random.uniform(0.5, 45.0), 2)
    minutes = offset // 60
    seconds = offset % 60
    h = 9 + (30 + minutes) // 60
    m = (30 + minutes) % 60
    time_str = f"{h:02d}:{m:02d}:{seconds:02d}"
    reason = random.choice(NEWS_POOL)
    n = random.randint(1, min(3, len(concepts)))
    tags = concepts[:n]

    return {
        'id': f"{code}-{int(time.time()*1000)}-{random.randint(100,999)}",
        'code': code,
        'name': name,
        'type': tmpl['type'],
        'label': tmpl['label'],
        'price': round(random.uniform(5, 300), 2),
        'change': change,
        'speed': speed,
        'amount': amount,
        'time': time_str,
        'timestamp': int(time.time() * 1000),
        'reason': reason,
        'concepts': tags,
    }

# 预生成演示数据
demo_alerts = []
t = 0
while t < 1800:
    demo_alerts.append(gen_alert(t))
    t += random.randint(3, 25)
demo_alerts.reverse()
print(f"[演示] 生成 {len(demo_alerts)} 条模拟异动")

clients = set()
feed_index = 0

async def ws_handler(websocket):
    clients.add(websocket)
    print(f"[WS] +1 客户端 ({len(clients)})")
    try:
        await websocket.send(json.dumps({
            'type': 'init',
            'alerts': demo_alerts[:20],
            'market': 'open'
        }))
        async for msg in websocket:
            data = json.loads(msg)
            if data.get('action') == 'refresh':
                await websocket.send(json.dumps({
                    'type': 'init', 'alerts': demo_alerts[:50], 'market': 'open'
                }))
            elif data.get('action') == 'get_klines':
                code = data.get('code', '')
                days = min(int(data.get('days', 60)), 150)
                klines = fetch_stock_klines(code, days)
                await websocket.send(json.dumps({
                    'type': 'klines',
                    'data': klines
                }))
                print(f"[K线] {code} {days}日 → {len(klines)}条")
            elif data.get('action') == 'get_sentiment':
                # 获取情绪数据并返回
                sentiment = gen_sentiment_data()
                await websocket.send(json.dumps({
                    'type': 'sentiment',
                    'data': sentiment
                }))
                print(f"[情绪] 推送情绪数据")
            elif data.get('action') == 'update_schemes':
                pass  # 演示模式忽略方案更新
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        clients.discard(websocket)
        print(f"[WS] -1 客户端 ({len(clients)})")

async def broadcast(data):
    if not clients: return
    msg = json.dumps(data)
    await asyncio.gather(*[ws.send(msg) for ws in clients.copy()], return_exceptions=True)

async def feed_loop():
    global feed_index
    feed_index = 20
    while True:
        await asyncio.sleep(random.uniform(2, 5))
        if feed_index < len(demo_alerts):
            alert = demo_alerts[feed_index]
            feed_index += 1
        else:
            alert = gen_alert(random.randint(0, 1800))
        now = datetime.now()
        alert['time'] = now.strftime('%H:%M:%S')
        alert['timestamp'] = int(time.time() * 1000)
        await broadcast({'type': 'alerts', 'items': [alert]})
        print(f"[推送] {alert['name']} {alert['label']} {'+' if alert['change']>=0 else ''}{alert['change']}%")

async def main():
    # 监听所有接口，Railway 需要
    server = await websockets.serve(ws_handler, "0.0.0.0", WS_PORT)
    print(f"[StockRadar 演示引擎] ws://0.0.0.0:{WS_PORT}")
    await feed_loop()

if __name__ == '__main__':
    asyncio.run(main())
