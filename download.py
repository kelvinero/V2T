#!/usr/bin/env python3
"""抖音视频下载脚本 - 去水印下载

用法:
    python download.py <抖音视频链接> [输出目录]

示例:
    python download.py https://www.douyin.com/video/7653500257761758504
    python download.py https://v.douyin.com/7E4NlS4O3ig/ ./downloads

依赖:
    pip install requests

前置条件:
    需要在浏览器中登录抖音后，从浏览器复制 Cookie 填入 COOKIE 环境变量
    或使用 --cookie 参数指定
"""
import re
import sys
import os
import json
import requests
from urllib.parse import urlparse, parse_qs, unquote


# ---------- 配置 ----------
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.douyin.com/",
    "Cookie": os.environ.get("DOUYIN_COOKIE", ""),
}

API_BASE = "https://www.douyin.com"


def parse_douyin_url(url: str) -> str:
    """解析抖音链接，提取视频 ID"""
    url = url.strip()

    # 处理短链接
    if "v.douyin.com" in url:
        resp = requests.head(url, headers=DEFAULT_HEADERS, allow_redirects=True, timeout=10)
        final_url = resp.url
        url = final_url

    # 提取视频 ID
    # 格式: https://www.douyin.com/video/7653500257761758504
    # 或: https://www.douyin.com/video/7653500257761758504?modal_id=xxx
    m = re.search(r'/video/(\d+)', url)
    if m:
        return m.group(1)

    # 从 URL 参数提取 modal_id
    parsed = urlparse(url)
    modal_id = parse_qs(parsed.query).get("modal_id", [None])[0]
    if modal_id and modal_id.isdigit():
        return modal_id

    # 路径最后一部分
    path_parts = [p for p in parsed.path.split("/") if p.isdigit()]
    if path_parts:
        return path_parts[-1]

    raise ValueError(f"无法从链接提取视频 ID: {url}")


def get_video_info(aweme_id: str) -> dict:
    """调用抖音 API 获取视频信息"""
    params = {
        "aweme_id": aweme_id,
        "aid": 6383,
        "device_platform": "webapp",
        "channel": "channel_pc_web",
        "version_code": "170400",
        "version_name": "17.4.0",
        "platform": "PC",
        "pc_client_type": 1,
        "cookie_enabled": "true",
        "screen_width": "1920",
        "screen_height": "1080",
        "browser_language": "zh-CN",
        "browser_platform": "Win32",
        "browser_name": "Chrome",
        "browser_version": "124.0.0.0",
    }

    resp = requests.get(
        f"{API_BASE}/aweme/v1/web/aweme/detail/",
        params=params,
        headers=DEFAULT_HEADERS,
        timeout=15,
    )
    data = resp.json()

    if data.get("status_code") != 0:
        raise ValueError(f"API 错误: {data.get('status_msg', '未知错误')}")

    aweme = data.get("aweme_list", [{}])[0]
    if not aweme:
        aweme = data.get("aweme_detail", {})

    return aweme


def get_download_urls(aweme: dict) -> list[dict]:
    """从视频信息中提取下载链接"""
    downloads = []
    aweme_id = aweme.get("aweme_id", "unknown")

    # 视频
    if aweme.get("media_type") == 2:
        # 图文
        for i, img in enumerate(aweme.get("images", [])):
            urls = img.get("url_list", [])
            if urls:
                downloads.append({
                    "type": "image",
                    "filename": f"{aweme_id}_img{i+1}.jpg",
                    "url": unquote(urls[0]),
                })
    else:
        # 视频
        play_addr = aweme.get("video", {}).get("play_addr", {})
        uri = play_addr.get("uri")
        if uri:
            play_url = f"https://www.douyin.com/aweme/v1/play/?video_id={uri}"
            downloads.append({
                "type": "video",
                "filename": f"{aweme_id}.mp4",
                "url": play_url,
            })

    # 封面
    cover_url = aweme.get("video", {}).get("cover", {}).get("url_list", [])
    if cover_url:
        downloads.append({
            "type": "cover",
            "filename": f"{aweme_id}_cover.jpg",
            "url": unquote(cover_url[0]),
        })

    # 背景音乐
    music_url = aweme.get("music", {}).get("play_url", {}).get("url_list", [])
    if music_url:
        downloads.append({
            "type": "music",
            "filename": f"{aweme_id}.mp3",
            "url": unquote(music_url[0]),
        })

    return downloads


def download_file(url: str, filepath: str) -> None:
    """下载文件"""
    headers = {
        **DEFAULT_HEADERS,
        "Referer": "https://www.douyin.com/",
    }
    resp = requests.get(url, headers=headers, stream=True, timeout=60)
    resp.raise_for_status()

    total = int(resp.headers.get("content-length", 0))
    downloaded = 0

    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded / total * 100
                print(f"\r  {filepath}: {pct:.0f}% ({downloaded}/{total}) ", end="", flush=True)

    print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    video_url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "downloads"

    os.makedirs(output_dir, exist_ok=True)

    # 1. 解析视频 ID
    print(f"解析链接: {video_url}")
    aweme_id = parse_douyin_url(video_url)
    print(f"视频 ID: {aweme_id}")

    # 2. 获取视频信息
    print("获取视频信息...")
    aweme = get_video_info(aweme_id)
    print(f"标题: {aweme.get('desc', '无标题')[:60]}")
    print(f"作者: {aweme.get('author', {}).get('nickname', '未知')}")

    # 3. 获取下载链接
    downloads = get_download_urls(aweme)
    if not downloads:
        print("未找到可下载的资源")
        sys.exit(1)

    # 4. 下载
    print(f"\n下载 ({len(downloads)} 个文件):")
    for d in downloads:
        filepath = os.path.join(output_dir, d["filename"])
        download_file(d["url"], filepath)
        print(f"  ✅ {d['filename']}")


if __name__ == "__main__":
    main()
