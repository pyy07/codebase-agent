import React from 'react'
import { interpolate, useCurrentFrame } from 'remotion'

interface Scene5CTAProps {
  frame: number
  fps: number
}

export const Scene5CTA: React.FC<Scene5CTAProps> = ({ frame }) => {
  const opacity = interpolate(frame, [0, 30, 240, 270], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  })

  const scale = interpolate(frame, [0, 60], [0.9, 1], {
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
      }}
    >
      <div
        style={{
          transform: `scale(${scale})`,
          textAlign: 'center',
        }}
      >
        <h2
          style={{
            fontSize: 64,
            fontWeight: 700,
            color: '#ffffff',
            marginBottom: 40,
          }}
        >
          开始使用
        </h2>
        <p
          style={{
            fontSize: 32,
            color: '#ffffff',
            marginBottom: 60,
            opacity: 0.9,
          }}
        >
          让 AI Agent 帮你解决代码问题
        </p>
        <div
          style={{
            display: 'inline-block',
            background: 'rgba(255, 255, 255, 0.2)',
            borderRadius: 12,
            padding: '20px 40px',
            fontSize: 24,
            color: '#ffffff',
            fontWeight: 600,
            border: '2px solid rgba(255, 255, 255, 0.3)',
            backdropFilter: 'blur(10px)',
          }}
        >
          GitHub / 文档 / 演示
        </div>
      </div>
    </div>
  )
}
