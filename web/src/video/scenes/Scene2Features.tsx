import React from 'react'
import { interpolate, useCurrentFrame } from 'remotion'
import { FeatureCard } from '../components/FeatureCard'

interface Scene2FeaturesProps {
  frame: number
  fps: number
}

const features = [
  { icon: '🤖', title: '智能分析', desc: '基于 LangGraph Agent 框架' },
  { icon: '💬', title: '交互式分析', desc: 'Agent 主动请求用户输入' },
  { icon: '📚', title: '多数据源', desc: '代码、日志、数据库' },
  { icon: '🔍', title: '代码检索', desc: '智能检索相关代码' },
]

export const Scene2Features: React.FC<Scene2FeaturesProps> = ({ frame }) => {
  const opacity = interpolate(frame, [0, 30, 240, 270], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  })

  const yOffset = interpolate(frame, [0, 60], [50, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  })

  return (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        width: '100%',
        height: '100%',
        opacity,
        transform: `translateY(${yOffset}px)`,
      }}
    >
      <h2
        style={{
          fontSize: 48,
          fontWeight: 700,
          color: '#ffffff',
          marginBottom: 60,
          textAlign: 'center',
        }}
      >
        核心功能
      </h2>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: 40,
          maxWidth: 1200,
          padding: '0 40px',
        }}
      >
        {features.map((feature, index) => (
          <FeatureCard
            key={index}
            icon={feature.icon}
            title={feature.title}
            description={feature.desc}
            frame={frame}
            startFrame={60 + index * 30}
          />
        ))}
      </div>
    </div>
  )
}
