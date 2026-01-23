# Remotion 推广视频项目

本项目使用 Remotion 制作 Codebase Driven Agent 的推广视频。

## 项目结构

```
web/src/video/
├── scenes/          # 视频场景组件
│   ├── PromoVideo.tsx      # 主视频组件（场景切换逻辑）
│   ├── Scene1Intro.tsx      # 场景1：项目介绍和 Logo
│   ├── Scene2Features.tsx   # 场景2：核心功能展示
│   ├── Scene3Workflow.tsx   # 场景3：工作流程演示
│   ├── Scene4TechStack.tsx  # 场景4：技术栈展示
│   └── Scene5CTA.tsx        # 场景5：行动号召
├── components/      # 可复用组件
│   ├── Logo.tsx            # Logo 组件
│   ├── FadeInText.tsx      # 淡入文字组件
│   ├── FeatureCard.tsx     # 功能卡片组件
│   ├── BackgroundAudio.tsx # 背景音乐组件
│   └── SoundEffect.tsx     # 音效组件
├── assets/          # 视频资源（图片、字体等）
├── Root.tsx         # Remotion 根组件（注册所有 compositions）
├── remotion-entry.tsx  # Remotion 入口文件
└── index.ts         # 导出文件
```

## 开发视频

### 启动 Remotion Studio

```bash
cd web
npm run video:dev
```

Remotion Studio 会在浏览器中打开（默认 http://localhost:3001），你可以：
- 实时预览视频
- 调整视频参数
- 测试动画效果
- 修改代码并热重载

### 修改视频内容

1. **修改场景内容**：编辑 `scenes/` 目录下的场景组件
2. **调整动画**：修改 `frame` 和 `interpolate` 参数
3. **添加新场景**：在 `PromoVideo.tsx` 中添加新的场景组件
4. **自定义样式**：修改组件的 `style` 属性

### 导出视频

#### 基本导出

```bash
cd web
npm run video:render
```

视频将导出为 `web/out/video.mp4`（1920x1080，30fps，H.264 编码）。

#### 自定义导出参数

```bash
cd web

# 导出高质量视频
npx remotion render PromoVideo out/promo-hq.mp4 --codec=h264 --crf=18

# 导出 WebM 格式
npx remotion render PromoVideo out/promo.webm --codec=vp9

# 自定义分辨率
npx remotion render PromoVideo out/promo-4k.mp4 --scale=2

# 导出特定帧范围
npx remotion render PromoVideo out/promo-segment.mp4 --frames=0-300
```

## 视频结构

当前视频包含 5 个场景，总时长约 60 秒（1800 帧 @ 30fps）：

1. **场景1（0-10秒）**：项目介绍和 Logo 展示
2. **场景2（10-20秒）**：核心功能展示（智能分析、交互式分析、多数据源、代码检索）
3. **场景3（20-30秒）**：工作流程演示（4 步流程）
4. **场景4（30-40秒）**：技术栈展示（Backend、Frontend、AI/LLM）
5. **场景5（40-50秒）**：行动号召（CTA）

## 自定义视频

### 修改视频时长

编辑 `web/src/video/Root.tsx`：

```typescript
<Composition
  id="PromoVideo"
  component={PromoVideo}
  durationInFrames={1800} // 修改这里：1800 = 60秒 @ 30fps
  fps={30}
  width={1920}
  height={1080}
/>
```

### 修改场景时长

编辑 `web/src/video/scenes/PromoVideo.tsx`：

```typescript
const SCENE_DURATION = 300 // 修改这里：300 = 10秒 @ 30fps
```

### 添加新场景

1. 在 `scenes/` 目录创建新场景组件（如 `Scene6New.tsx`）
2. 在 `PromoVideo.tsx` 中导入并添加场景切换逻辑
3. 更新 `SCENE_DURATION` 和场景索引

## 资源文件

将图片、字体等资源放在 `assets/` 目录，然后在组件中导入：

```typescript
import logoImage from '../assets/logo.png'

// 在组件中使用
<img src={logoImage} alt="Logo" />
```

## 音频支持

视频支持添加背景音乐和音效：

1. **准备音频文件**：将音频文件放在 `public/audio/` 目录下
2. **启用背景音乐**：在 `PromoVideo.tsx` 中取消注释 `BackgroundAudio` 组件
3. **添加音效**：在场景组件中使用 `SoundEffect` 组件

详细说明请查看 [音频使用指南](AUDIO.md)。

## 批量导出

使用批量导出脚本一次性生成多种质量的视频：

```bash
cd web
npm run video:export:all
```

这将导出：
- 高质量 MP4 (CRF 18)
- 中等质量 MP4 (CRF 23)
- 低质量 MP4 (CRF 28)
- WebM 格式 (VP9)

## 更多文档

- [导出指南](EXPORT.md) - 详细的视频导出和优化说明
- [性能优化](PERFORMANCE.md) - 性能优化最佳实践
- [测试指南](TESTING.md) - 视频测试和验证步骤
- [音频使用指南](AUDIO.md) - 音频添加和使用说明

## 参考资源

- [Remotion 官方文档](https://www.remotion.dev/docs)
- [Remotion 示例](https://www.remotion.dev/docs/examples)
- [Remotion API 参考](https://www.remotion.dev/docs/remotion)
