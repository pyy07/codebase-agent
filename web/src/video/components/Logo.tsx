import React from 'react'

interface LogoProps {
  size?: number
}

export const Logo: React.FC<LogoProps> = ({ size = 100 }) => {
  return (
    <div
      style={{
        width: size,
        height: size,
        background: 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)',
        borderRadius: size * 0.28,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'white',
        fontSize: size * 0.5,
        fontWeight: 700,
        boxShadow: `0 ${size * 0.1}px ${size * 0.2}px rgba(59, 130, 246, 0.3)`,
      }}
    >
      CA
    </div>
  )
}
