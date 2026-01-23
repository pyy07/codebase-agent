import React from 'react'
import { Audio, useVideoConfig } from 'remotion'

interface BackgroundAudioProps {
  /**
   * 音频文件路径（相对于 public 目录或绝对 URL）
   * 例如：'/audio/background.mp3' 或 'https://example.com/audio.mp3'
   */
  src?: string
  /**
   * 音频音量（0-1）
   * @default 0.5
   */
  volume?: number
  /**
   * 是否循环播放
   * @default true
   */
  loop?: boolean
  /**
   * 音频开始时间（秒）
   * @default 0
   */
  startFrom?: number
}

/**
 * 背景音乐组件
 * 
 * 使用示例：
 * ```tsx
 * <BackgroundAudio 
 *   src="/audio/background.mp3" 
 *   volume={0.3} 
 *   loop={true} 
 * />
 * ```
 * 
 * 注意：
 * - 音频文件应放在 public/audio/ 目录下
 * - 如果没有提供 src，组件不会渲染任何内容（静音模式）
 * - 建议使用 MP3 格式以确保兼容性
 */
export const BackgroundAudio: React.FC<BackgroundAudioProps> = ({
  src,
  volume = 0.5,
  loop = true,
  startFrom = 0,
}) => {
  const { fps } = useVideoConfig()

  // 如果没有提供音频源，不渲染任何内容
  if (!src) {
    return null
  }

  return (
    <Audio
      src={src}
      volume={volume}
      loop={loop}
      startFrom={startFrom * fps} // 转换为帧数
    />
  )
}
