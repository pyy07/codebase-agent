import React from 'react'
import { useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion'
import { Scene1Intro } from './Scene1Intro'
import { Scene2Features } from './Scene2Features'
import { Scene3Workflow } from './Scene3Workflow'
import { Scene4TechStack } from './Scene4TechStack'
import { Scene5CTA } from './Scene5CTA'
import { BackgroundAudio } from '../components/BackgroundAudio'

const SCENE_DURATION = 150 // 每个场景 5 秒 @ 30fps

/**
 * 主视频组件
 * 
 * 音频配置：
 * - 如需添加背景音乐，取消注释下面的 BackgroundAudio 组件
 * - 将音频文件放在 public/audio/ 目录下
 * - 建议使用 MP3 格式，时长与视频匹配或更长（会自动循环）
 */
export const PromoVideo: React.FC = () => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()

  // 场景切换逻辑
  const sceneIndex = Math.floor(frame / SCENE_DURATION)
  const sceneFrame = frame % SCENE_DURATION

  return (
    <div
      style={{
        flex: 1,
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        width: '100%',
        height: '100%',
      }}
    >
      {/* 背景音乐（可选）- 取消注释以启用 */}
      {/* <BackgroundAudio 
        src="/audio/background.mp3" 
        volume={0.3} 
        loop={true} 
      /> */}

      {sceneIndex === 0 && <Scene1Intro frame={sceneFrame} fps={fps} />}
      {sceneIndex === 1 && <Scene2Features frame={sceneFrame} fps={fps} />}
      {sceneIndex === 2 && <Scene3Workflow frame={sceneFrame} fps={fps} />}
      {sceneIndex === 3 && <Scene4TechStack frame={sceneFrame} fps={fps} />}
      {sceneIndex === 4 && <Scene5CTA frame={sceneFrame} fps={fps} />}
      {sceneIndex >= 5 && <Scene5CTA frame={sceneFrame} fps={fps} />}
    </div>
  )
}
