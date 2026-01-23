import React from 'react'
import { interpolate, useCurrentFrame } from 'remotion'

interface Scene4TechStackProps {
  frame: number
  fps: number
}

const techStack = [
  { category: 'Backend', items: ['FastAPI', 'LangChain', 'LangGraph'] },
  { category: 'Frontend', items: ['React', 'TypeScript', 'Tailwind CSS'] },
  { category: 'AI/LLM', items: ['OpenAI', 'Anthropic', 'Custom API'] },
]

export const Scene4TechStack: React.FC<Scene4TechStackProps> = ({ frame }) => {
  const opacity = interpolate(frame, [0, 15, 120, 135], [0, 1, 1, 0], {
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
        技术栈
      </h2>
      <div
        style={{
          display: 'flex',
          gap: 60,
          maxWidth: 1400,
        }}
      >
        {techStack.map((stack, index) => {
          const cardOpacity = interpolate(
            frame,
            [index * 20, index * 20 + 15],
            [0, 1],
            {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }
          )

          return (
            <div
              key={index}
              style={{
                background: 'rgba(255, 255, 255, 0.1)',
                borderRadius: 20,
                padding: 40,
                minWidth: 300,
                opacity: cardOpacity,
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
              }}
            >
              <h3
                style={{
                  fontSize: 32,
                  fontWeight: 700,
                  color: '#ffffff',
                  marginBottom: 30,
                  textAlign: 'center',
                }}
              >
                {stack.category}
              </h3>
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 15,
                }}
              >
                {stack.items.map((item, itemIndex) => (
                  <div
                    key={itemIndex}
                    style={{
                      fontSize: 20,
                      color: '#ffffff',
                      textAlign: 'center',
                      padding: '10px 0',
                      borderBottom:
                        itemIndex < stack.items.length - 1
                          ? '1px solid rgba(255, 255, 255, 0.1)'
                          : 'none',
                    }}
                  >
                    {item}
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
