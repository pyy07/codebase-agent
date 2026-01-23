import React from 'react'
import { interpolate } from 'remotion'

interface FadeInTextProps {
  text: string
  frame: number
  startFrame: number
  fontSize?: number
  fontWeight?: number
  color?: string
  style?: React.CSSProperties
}

export const FadeInText: React.FC<FadeInTextProps> = ({
  text,
  frame,
  startFrame,
  fontSize = 32,
  fontWeight = 400,
  color = '#000000',
  style,
}) => {
  const opacity = interpolate(
    frame,
    [startFrame, startFrame + 15],
    [0, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    }
  )

  const yOffset = interpolate(
    frame,
    [startFrame, startFrame + 15],
    [20, 0],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    }
  )

  return (
    <div
      style={{
        fontSize,
        fontWeight,
        color,
        opacity,
        transform: `translateY(${yOffset}px)`,
        textAlign: 'center',
        ...style,
      }}
    >
      {text}
    </div>
  )
}
