import React from 'react'
import { interpolate, useCurrentFrame, spring } from 'remotion'
import { Logo } from '../components/Logo'
import { FadeInText } from '../components/FadeInText'

interface Scene1IntroProps {
  frame: number
  fps: number
}

export const Scene1Intro: React.FC<Scene1IntroProps> = ({ frame, fps }) => {
  const logoScale = spring({
    frame,
    fps,
    config: {
      damping: 10,
      stiffness: 100,
      mass: 1,
    },
    from: 0,
    to: 1,
  })

  const opacity = interpolate(frame, [0, 15, 75, 90], [0, 1, 1, 0], {
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
          transform: `scale(${logoScale})`,
          marginBottom: 60,
        }}
      >
        <Logo size={200} />
      </div>
      <FadeInText
        text="Codebase Driven Agent"
        frame={frame}
        startFrame={30}
        fontSize={64}
        fontWeight={700}
        color="#ffffff"
      />
      <FadeInText
        text="基于代码库驱动的通用 AI Agent 平台"
        frame={frame}
        startFrame={60}
        fontSize={32}
        fontWeight={400}
        color="#ffffff"
        style={{ marginTop: 30, opacity: 0.9 }}
      />
    </div>
  )
}
