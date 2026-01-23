import React from 'react'
import { interpolate, useCurrentFrame } from 'remotion'

interface Scene3WorkflowProps {
  frame: number
  fps: number
}

const steps = [
  { step: 1, text: '用户提交问题' },
  { step: 2, text: 'Agent 规划分析' },
  { step: 3, text: '调用工具执行' },
  { step: 4, text: '生成解决方案' },
]

export const Scene3Workflow: React.FC<Scene3WorkflowProps> = ({ frame }) => {
  const opacity = interpolate(frame, [0, 30, 240, 270], [0, 1, 1, 0], {
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
      <h2
        style={{
          fontSize: 48,
          fontWeight: 700,
          color: '#ffffff',
          marginBottom: 80,
        }}
      >
        工作流程
      </h2>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 40,
          maxWidth: 1400,
        }}
      >
        {steps.map((item, index) => {
          const stepOpacity = interpolate(
            frame,
            [index * 50, index * 50 + 30],
            [0, 1],
            {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }
          )

          const stepScale = interpolate(
            frame,
            [index * 50, index * 50 + 30],
            [0.8, 1],
            {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }
          )

          return (
            <div key={index} style={{ display: 'flex', alignItems: 'center' }}>
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  opacity: stepOpacity,
                  transform: `scale(${stepScale})`,
                }}
              >
                <div
                  style={{
                    width: 120,
                    height: 120,
                    borderRadius: '50%',
                    background: 'rgba(255, 255, 255, 0.2)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 48,
                    fontWeight: 700,
                    color: '#ffffff',
                    marginBottom: 20,
                    border: '3px solid rgba(255, 255, 255, 0.5)',
                  }}
                >
                  {item.step}
                </div>
                <div
                  style={{
                    fontSize: 24,
                    color: '#ffffff',
                    fontWeight: 500,
                    textAlign: 'center',
                  }}
                >
                  {item.text}
                </div>
              </div>
              {index < steps.length - 1 && (
                <div
                  style={{
                    width: 60,
                    height: 3,
                    background: 'rgba(255, 255, 255, 0.5)',
                    margin: '0 20px',
                  }}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
