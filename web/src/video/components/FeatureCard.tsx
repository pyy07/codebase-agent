import React from 'react'
import { interpolate } from 'remotion'

interface FeatureCardProps {
  icon: string
  title: string
  description: string
  frame: number
  startFrame: number
}

export const FeatureCard: React.FC<FeatureCardProps> = ({
  icon,
  title,
  description,
  frame,
  startFrame,
}) => {
  const opacity = interpolate(
    frame,
    [startFrame, startFrame + 30],
    [0, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    }
  )

  const scale = interpolate(
    frame,
    [startFrame, startFrame + 30],
    [0.9, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    }
  )

  return (
    <div
      style={{
        background: 'rgba(255, 255, 255, 0.1)',
        borderRadius: 16,
        padding: 30,
        opacity,
        transform: `scale(${scale})`,
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(255, 255, 255, 0.2)',
        textAlign: 'center',
      }}
    >
      <div
        style={{
          fontSize: 48,
          marginBottom: 20,
        }}
      >
        {icon}
      </div>
      <h3
        style={{
          fontSize: 24,
          fontWeight: 700,
          color: '#ffffff',
          marginBottom: 10,
        }}
      >
        {title}
      </h3>
      <p
        style={{
          fontSize: 16,
          color: '#ffffff',
          opacity: 0.9,
        }}
      >
        {description}
      </p>
    </div>
  )
}
