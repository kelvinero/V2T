#!/usr/bin/env python3
"""Whisper 转写脚本 - 抖音视频对白提取

用法:
    python transcribe.py <输入音频路径> <输出文字稿路径> [模型大小]

示例:
    python transcribe.py audio.wav transcript.txt small
    python transcribe.py audio.wav transcript.txt base

依赖安装:
    pip install faster-whisper

前置工具:
    ffmpeg  - https://www.gyan.dev/ffmpeg/builds/
    whisper 模型 - 首次运行自动下载 (small/base/medium/large)
"""
import sys
from faster_whisper import WhisperModel

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    audio_path = sys.argv[1]
    output_path = sys.argv[2]
    model_size = sys.argv[3] if len(sys.argv) > 3 else "small"

    print(f"加载模型: {model_size}")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    print(f"转写: {audio_path}")
    segments, info = model.transcribe(audio_path, language="zh", beam_size=5, vad_filter=True)

    print(f"检测到语言: {info.language} (概率: {info.language_probability:.2f})")
    print(f"时长: {info.duration:.1f}s")
    print("---")

    with open(output_path, "w", encoding="utf-8") as f:
        for seg in segments:
            line = f"[{seg.start:.1f}s-{seg.end:.1f}s] {seg.text.strip()}"
            print(line)
            f.write(line + "\n")

    print(f"---")
    print(f"已保存到: {output_path}")

if __name__ == "__main__":
    main()
