# 音频文件目录

此目录用于存放 Remotion 视频的音频文件。

## 目录结构

```
public/audio/
├── background.mp3    # 背景音乐（可选）
├── click.mp3         # 点击音效（可选）
└── transition.mp3   # 过渡音效（可选）
```

## 使用说明

1. **添加音频文件**：将音频文件（MP3、WAV、OGG）放在此目录下
2. **在代码中引用**：使用 `/audio/filename.mp3` 路径引用音频文件
3. **启用音频**：在 `PromoVideo.tsx` 中取消注释 `BackgroundAudio` 组件

## 音频要求

- **格式**：推荐 MP3（最佳兼容性）
- **采样率**：44.1kHz 或 48kHz
- **比特率**：背景音乐 128-192 kbps，音效 96-128 kbps
- **时长**：背景音乐建议与视频时长匹配或更长（会自动循环）

## 免费音频资源

- [Freesound](https://freesound.org/) - 免费音效库
- [YouTube Audio Library](https://www.youtube.com/audiolibrary) - 免费背景音乐
- [Incompetech](https://incompetech.com/music/) - 免费背景音乐

## 更多信息

查看 [音频使用指南](../../src/video/AUDIO.md) 了解详细的使用方法。
