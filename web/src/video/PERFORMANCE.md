# 视频性能优化指南

本文档提供 Remotion 视频性能优化的最佳实践。

## 渲染性能优化

### 1. 组件优化

#### 使用 React.memo

对于不经常变化的组件，使用 `React.memo` 避免不必要的重渲染：

```typescript
import React from 'react'
import { memo } from 'react'

export const Logo = memo(({ size }: { size: number }) => {
  // Logo 组件实现
})
```

#### 避免内联对象和函数

```typescript
// ❌ 不好：每次渲染都创建新对象
<div style={{ color: 'white', fontSize: 20 }}>

// ✅ 好：使用常量或 useMemo
const style = { color: 'white', fontSize: 20 }
<div style={style}>
```

#### 使用 useMemo 缓存计算结果

```typescript
import { useMemo } from 'react'
import { useCurrentFrame } from 'remotion'

export const MyScene = () => {
  const frame = useCurrentFrame()
  
  // 缓存复杂计算
  const expensiveValue = useMemo(() => {
    return complexCalculation(frame)
  }, [frame])
  
  return <div>{expensiveValue}</div>
}
```

### 2. 动画优化

#### 使用 spring 而非 interpolate（适合弹性动画）

```typescript
import { spring } from 'remotion'

// ✅ 适合弹性动画
const scale = spring({
  frame,
  fps,
  config: { damping: 10, stiffness: 100 }
})

// ✅ 适合线性动画
const opacity = interpolate(frame, [0, 30], [0, 1])
```

#### 避免过度复杂的插值

```typescript
// ❌ 不好：太多关键帧
const value = interpolate(frame, [0, 10, 20, 30, 40, 50], [0, 1, 0, 1, 0, 1])

// ✅ 好：简化关键帧
const value = interpolate(frame, [0, 30], [0, 1], {
  extrapolateLeft: 'clamp',
  extrapolateRight: 'clamp'
})
```

### 3. 资源优化

#### 图片优化

```typescript
// 使用 WebP 格式（更小）
import logoImage from '../assets/logo.webp'

// 预加载图片
<img src={logoImage} alt="Logo" loading="eager" />
```

#### 字体优化

```typescript
// 使用系统字体或 Web 字体子集
const fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
```

### 4. 场景切换优化

#### 延迟加载场景组件

```typescript
import { lazy, Suspense } from 'react'

const Scene2 = lazy(() => import('./Scene2Features'))

export const PromoVideo = () => {
  const sceneIndex = Math.floor(frame / SCENE_DURATION)
  
  return (
    <Suspense fallback={<div>Loading...</div>}>
      {sceneIndex === 1 && <Scene2 />}
    </Suspense>
  )
}
```

#### 避免同时渲染多个场景

```typescript
// ✅ 好：只渲染当前场景
{sceneIndex === 0 && <Scene1 />}
{sceneIndex === 1 && <Scene2 />}

// ❌ 不好：同时渲染所有场景（隐藏）
<div style={{ display: sceneIndex === 0 ? 'block' : 'none' }}>
  <Scene1 />
</div>
```

## 渲染配置优化

### 1. 并发设置

```bash
# 根据 CPU 核心数设置并发
# 8 核 CPU：使用 6-8 个并发
npx remotion render PromoVideo out/video.mp4 --concurrency=8

# 4 核 CPU：使用 3-4 个并发
npx remotion render PromoVideo out/video.mp4 --concurrency=4
```

### 2. 内存管理

```bash
# 如果内存不足，减少并发
npx remotion render PromoVideo out/video.mp4 --concurrency=2

# 或降低分辨率
npx remotion render PromoVideo out/video.mp4 --scale=0.5
```

### 3. 缓存优化

Remotion 默认启用 Webpack 缓存，可以加速后续渲染：

```typescript
// remotion.config.ts
import { Config } from '@remotion/cli/config'

// 启用缓存（默认已启用）
Config.setCachingEnabled(true)
```

## 开发时性能优化

### 1. 使用 Remotion Studio 预览

开发时使用 Studio 预览，而不是每次都导出：

```bash
npm run video:dev
```

Studio 提供：
- 实时预览
- 帧级调试
- 快速迭代

### 2. 降低预览分辨率

在 Studio 中降低预览分辨率以加快预览速度。

### 3. 分段测试

只渲染需要测试的场景：

```bash
# 只渲染场景1（0-300帧）
npx remotion render PromoVideo out/test-scene1.mp4 --frames=0-300
```

## 性能监控

### 1. 渲染时间统计

```bash
# 显示详细渲染信息
npx remotion render PromoVideo out/video.mp4 --log=verbose
```

### 2. 内存使用监控

在渲染时监控内存使用，如果超过系统限制，减少并发数。

### 3. 帧率检查

在 Studio 中检查预览帧率，确保动画流畅。

## 最佳实践总结

1. **组件优化**
   - 使用 `React.memo` 避免不必要的重渲染
   - 避免内联对象和函数
   - 使用 `useMemo` 缓存计算结果

2. **动画优化**
   - 选择合适的动画函数（spring vs interpolate）
   - 简化关键帧
   - 避免过度复杂的计算

3. **资源优化**
   - 使用优化的图片格式（WebP）
   - 使用系统字体或字体子集
   - 预加载关键资源

4. **渲染优化**
   - 根据 CPU 核心数设置并发
   - 合理使用内存
   - 启用缓存

5. **开发流程**
   - 使用 Studio 预览而非频繁导出
   - 分段测试场景
   - 监控性能指标

## 参考资源

- [Remotion 性能优化](https://www.remotion.dev/docs/performance)
- [React 性能优化](https://react.dev/learn/render-and-commit)
- [Remotion 最佳实践](https://www.remotion.dev/docs/best-practices)
