# 音频使用指南

本文档说明如何在 Remotion 视频中添加背景音乐和音效。

## 快速开始

### 1. 准备音频文件

将音频文件放在 `web/public/audio/` 目录下：

```
web/public/audio/
├── background.mp3    # 背景音乐
├── click.mp3         # 点击音效
└── transition.mp3    # 过渡音效
```

**音频格式建议**：
- **MP3**：最佳兼容性，推荐使用
- **WAV**：高质量但文件较大
- **OGG**：开源格式，浏览器支持良好

### 2. 添加背景音乐

在 `PromoVideo.tsx` 中启用背景音乐：

```tsx
import { BackgroundAudio } from '../components/BackgroundAudio'

export const PromoVideo: React.FC = () => {
  return (
    <div>
      {/* 背景音乐 */}
      <BackgroundAudio 
        src="/audio/background.mp3" 
        volume={0.3}      // 音量 0-1，建议 0.2-0.4
        loop={true}       // 循环播放
        startFrom={0}     // 从第 0 秒开始
      />
      
      {/* 视频内容 */}
      {/* ... */}
    </div>
  )
}
```

### 3. 添加音效

在场景组件中添加音效：

```tsx
import { SoundEffect } from '../components/SoundEffect'

export const Scene1Intro: React.FC<{ frame: number; fps: number }> = ({ frame, fps }) => {
  return (
    <div>
      {/* Logo 出现时的音效（第 2 秒，60 帧 @ 30fps） */}
      <SoundEffect 
        src="/audio/click.mp3" 
        startFrame={60} 
        volume={0.5} 
      />
      
      {/* 视频内容 */}
      {/* ... */}
    </div>
  )
}
```

## 组件 API

### BackgroundAudio

背景音乐组件，用于在整个视频中播放循环背景音乐。

**Props**：

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `src` | `string?` | - | 音频文件路径（相对于 public 目录） |
| `volume` | `number` | `0.5` | 音量（0-1） |
| `loop` | `boolean` | `true` | 是否循环播放 |
| `startFrom` | `number` | `0` | 音频开始时间（秒） |

**示例**：

```tsx
<BackgroundAudio 
  src="/audio/background.mp3" 
  volume={0.3} 
  loop={true} 
/>
```

### SoundEffect

音效组件，用于在特定帧播放短音效。

**Props**：

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `src` | `string` | - | 音效文件路径（必需） |
| `volume` | `number` | `0.7` | 音量（0-1） |
| `startFrame` | `number` | - | 触发音效的帧数（必需） |
| `durationInFrames` | `number` | `0` | 音效持续时间（帧数），0 表示播放完整音频 |

**示例**：

```tsx
<SoundEffect 
  src="/audio/click.mp3" 
  startFrame={60}      // 第 2 秒 @ 30fps
  volume={0.5} 
  durationInFrames={30} // 播放 1 秒
/>
```

## 最佳实践

### 1. 音量控制

- **背景音乐**：建议音量 0.2-0.4，确保不掩盖视频内容
- **音效**：建议音量 0.5-0.7，确保清晰可听但不刺耳
- **总体原则**：背景音乐 < 音效 < 旁白（如果有）

### 2. 音频时长

- **背景音乐**：建议时长与视频匹配或更长（会自动循环）
- **音效**：建议 0.5-2 秒，短促有力

### 3. 音频质量

- **采样率**：建议 44.1kHz 或 48kHz
- **比特率**：背景音乐建议 128-192 kbps，音效建议 96-128 kbps
- **格式**：MP3 格式最佳兼容性

### 4. 性能优化

- 使用压缩后的音频文件（MP3）
- 避免使用过长的音频文件
- 音效文件尽量小（< 100KB）

### 5. 时间同步

计算帧数的公式：

```typescript
// 秒数转帧数
const seconds = 5
const fps = 30
const frames = seconds * fps  // 150 帧

// 在组件中使用
<SoundEffect 
  src="/audio/click.mp3" 
  startFrame={150}  // 第 5 秒
/>
```

## 常见场景

### 场景切换音效

```tsx
// 在 PromoVideo.tsx 中
const SCENE_DURATION = 300 // 10 秒 @ 30fps

{sceneIndex === 1 && (
  <>
    {/* 场景切换音效 */}
    <SoundEffect 
      src="/audio/transition.mp3" 
      startFrame={SCENE_DURATION} 
      volume={0.4} 
    />
    <Scene2Features frame={sceneFrame} fps={fps} />
  </>
)}
```

### 文字出现音效

```tsx
// 在场景组件中
<FadeInText
  text="Codebase Driven Agent"
  frame={frame}
  startFrame={60}
/>

{/* 文字出现时的音效 */}
<SoundEffect 
  src="/audio/type.mp3" 
  startFrame={60} 
  volume={0.3} 
/>
```

### 淡入淡出背景音乐

```tsx
import { interpolate, useCurrentFrame } from 'remotion'

export const PromoVideo: React.FC = () => {
  const frame = useCurrentFrame()
  const { durationInFrames } = useVideoConfig()
  
  // 淡入淡出音量
  const volume = interpolate(
    frame,
    [0, 30, durationInFrames - 30, durationInFrames],
    [0, 0.3, 0.3, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  )
  
  return (
    <div>
      <BackgroundAudio 
        src="/audio/background.mp3" 
        volume={volume} 
        loop={true} 
      />
      {/* ... */}
    </div>
  )
}
```

## 音频资源推荐

### 免费音频资源

- [Freesound](https://freesound.org/) - 免费音效库
- [YouTube Audio Library](https://www.youtube.com/audiolibrary) - 免费背景音乐
- [Incompetech](https://incompetech.com/music/) - 免费背景音乐
- [Zapsplat](https://www.zapsplat.com/) - 免费音效（需注册）

### 音频编辑工具

- [Audacity](https://www.audacityteam.org/) - 免费音频编辑软件
- [FFmpeg](https://ffmpeg.org/) - 命令行音频处理工具

### 音频转换

使用 FFmpeg 转换音频格式：

```bash
# 转换为 MP3（128 kbps）
ffmpeg -i input.wav -codec:a libmp3lame -b:a 128k output.mp3

# 调整音量（降低 50%）
ffmpeg -i input.mp3 -af "volume=0.5" output.mp3

# 裁剪音频（前 10 秒）
ffmpeg -i input.mp3 -t 10 output.mp3
```

## 故障排除

### 音频不播放

1. **检查文件路径**：确保音频文件在 `public/audio/` 目录下
2. **检查文件格式**：确保使用支持的格式（MP3、WAV、OGG）
3. **检查浏览器控制台**：查看是否有错误信息
4. **检查音量设置**：确保 `volume` 不为 0

### 音频延迟

1. **预加载音频**：在 Remotion Studio 中，音频会自动预加载
2. **使用压缩格式**：MP3 比 WAV 加载更快
3. **优化文件大小**：减小音频文件大小

### 音频不同步

1. **检查帧数计算**：确保 `startFrame` 计算正确
2. **使用 `startFrom`**：BackgroundAudio 支持 `startFrom` 参数
3. **检查 FPS 设置**：确保视频 FPS 与音频匹配

## 参考资源

- [Remotion Audio 文档](https://www.remotion.dev/docs/audio)
- [Remotion useAudioData Hook](https://www.remotion.dev/docs/use-audio-data)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
