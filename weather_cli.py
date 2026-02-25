#!/usr/bin/env python3
"""
命令行天气查询工具
功能：
  1. 通过和风天气API获取实时天气
  2. 支持城市名称/ID查询
  3. 格式化输出天气信息（含emoji）
  4. 缓存机制避免频繁请求
用法：
  python weather_cli.py 北京
  python weather_cli.py --city 上海 --unit fahrenheit
"""

import requests
import argparse
import os
import json
import time
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置（从环境变量获取）
API_KEY = os.getenv('QWEATHER_API_KEY', '')
DEFAULT_CITY = os.getenv('DEFAULT_CITY', 'beijing')
CACHE_DIR = os.path.expanduser('~/.weather_cache')
CACHE_EXPIRY = 30 * 60  # 30分钟缓存

# 创建缓存目录
os.makedirs(CACHE_DIR, exist_ok=True)

def get_location_id(city_name):
    """获取城市ID（和风天气）"""
    url = f"https://geoapi.qweather.com/v2/city/lookup?location={city_name}&key={API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') == '200' and data.get('location'):
            return data['location'][0]['id'], data['location'][0]['name']
        else:
            print(f"⚠️  城市 '{city_name}' 未找到，请检查名称或尝试拼音")
            return None, None
    except Exception as e:
        print(f"❌ 获取城市ID失败: {str(e)}")
        return None, None

def get_weather_data(location_id):
    """获取天气数据（带缓存）"""
    cache_file = os.path.join(CACHE_DIR, f"{location_id}.json")
    now = time.time()
    
    # 检查缓存
    if os.path.exists(cache_file):
        file_mtime = os.path.getmtime(cache_file)
        if now - file_mtime < CACHE_EXPIRY:
            print("💾 使用缓存数据（30分钟内）")
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    # API请求
    url = f"https://devapi.qweather.com/v7/weather/now?location={location_id}&key={API_KEY}"
    
    try:
        print("📡 正在获取最新天气数据...")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') == '200':
            # 保存到缓存
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return data
        else:
            print(f"❌ API返回错误: {data.get('code')}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ 处理天气数据时出错: {str(e)}")
        return None

def format_weather_output(weather_data, city_name, unit='c'):
    """格式化输出天气信息"""
    if not weather_data or 'now' not in weather_data:
        return "❌ 无法获取天气数据"
    
    now = weather_data['now']
    temp_c = float(now['temp'])
    temp_f = temp_c * 9/5 + 32
    
    # 天气状况emoji映射
    weather_icons = {
        'Sunny': '☀️',
        'Cloudy': '⛅',
        'Overcast': '☁️',
        'Rain': '🌧️',
        'Snow': '❄️',
        'Thunder': '⚡',
        'Fog': '🌫️',
        'Haze': '🌫️'
    }
    
    # 获取天气图标
    icon = weather_icons.get(now['text'], '🌤️')
    
    # 温度显示
    if unit == 'f':
        temp_display = f"{temp_f:.1f}°F"
        feels_like = f"{(float(now['feelsLike'])*9/5+32):.1f}°F"
    else:
        temp_display = f"{temp_c:.1f}°C"
        feels_like = f"{now['feelsLike']}°C"
    
    # 获取当前时间（时区处理）
    tz = pytz.timezone('Asia/Shanghai')
    current_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M')
    
    # 构建输出
    output = f"""
{icon} {city_name} 天气 ({current_time})
━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌡️  温度: {temp_display}
😅  体感: {feels_like}
💧  湿度: {now['humidity']}%
💨  风速: {now['windSpeed']} km/h {now['windDir']}
👀  能见度: {now['vis']} km
━━━━━━━━━━━━━━━━━━━━━━━━━━━
更新时间: {weather_data['updateTime'].replace('T', ' ')}
"""
    return output

def main():
    parser = argparse.ArgumentParser(description='CLI天气查询工具')
    parser.add_argument('city', nargs='?', default=DEFAULT_CITY,
                        help='城市名称 (中文/拼音)，例如: 北京/beijing')
    parser.add_argument('--unit', choices=['c', 'f'], default='c',
                        help='温度单位: c(摄氏度) 或 f(华氏度)')
    parser.add_argument('--clear-cache', action='store_true',
                        help='清除所有缓存数据')
    
    args = parser.parse_args()
    
    # 清除缓存
    if args.clear_cache:
        import shutil
        shutil.rmtree(CACHE_DIR)
        os.makedirs(CACHE_DIR, exist_ok=True)
        print("✅ 缓存已清除")
        return
    
    # 检查API密钥
    if not API_KEY or API_KEY == 'your_api_key_here':
        print("❌ 错误: 未配置有效的和风天气API密钥")
        print("请在.env文件中设置QWEATHER_API_KEY，或参考.env.example")
        return 1
    
    # 获取城市ID
    location_id, found_city = get_location_id(args.city)
    if not location_id:
        return 1
    
    # 获取天气数据
    weather_data = get_weather_data(location_id)
    if not weather_data:
        return 1
    
    # 格式化输出
    output = format_weather_output(weather_data, found_city, args.unit)
    print(output)
    
    return 0

if __name__ == "__main__":
    exit(main())