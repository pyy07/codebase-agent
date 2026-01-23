import React from 'react'
import { Composition } from 'remotion'
import { PromoVideo } from './scenes/PromoVideo'

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="PromoVideo"
        component={PromoVideo}
        durationInFrames={1800} // 60秒 @ 30fps
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  )
}

// 导出为 Root 以符合 Remotion 约定
export const Root = RemotionRoot
