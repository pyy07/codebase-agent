const { contextBridge, ipcRenderer } = require('electron')

// 暴露安全的 API 给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  versions: {
    node: process.versions.node,
    chrome: process.versions.chrome,
    electron: process.versions.electron,
  },
  // 暴露后端 API 基础 URL
  // 在 Electron 打包应用中，前端通过 file:// 协议加载，需要完整的 URL
  apiBaseURL: 'http://localhost:8000',
  // 通过 IPC 从主进程获取 API key
  getApiKey: () => ipcRenderer.invoke('get-api-key'),
})
