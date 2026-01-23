import React from 'react'
import { Audio, useCurrentFrame, useVideoConfig } from 'remotion'

interface SoundEffectProps {
  /**
   * 音效文件路径
   */
  src: string
  /**
   * 音效音量（0-1）
   * @default 0.7
   */
  volume?: number
  /**
   * 触发音效的帧数
   */
  startFrame: number
  /**
   * 音效持续时间（帧数），如果为 0 则播放完整音频
   * @default 0
   */
  durationInFrames?: number
}

/**
 * 音效组件
 * 
 * 用于在特定帧播放音效（如点击声、提示音等）
 * 
 * 使用示例：
 * ```tsx
 * <SoundEffect 
 *   src="/audio/click.mp3" 
 *   startFrame={60} 
 *   volume={0.5} 
 * />
 * ```
 */
export const SoundEffect: React.FC<SoundEffectProps> = ({
  src,
  volume = 0.7,
  startFrame,
  durationInFrames = 0,
}) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()

  // 只在指定帧范围内播放
  const shouldPlay = frame >= startFrame && 
    (durationInFrames === 0 || frame < startFrame + durationInFrames)

  if (!shouldPlay) {
    return null
  }

  return (
    <Audio
      src={src}
      volume={volume}
      startFrom={startFrame}
      endAt={durationInFrames > 0 ? startFrame + durationInFrames : undefined}
    />
  )
}
