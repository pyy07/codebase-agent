const fs = require('fs');
const path = require('path');
const { extract } = require('extract-zip');

exports.default = async function(context) {
  const { packager } = context;
  const platform = packager.platform.name;
  
  // 清理可能被锁定的文件（在 electron-builder 开始打包之前）
  const releaseDir = path.join(packager.projectDir, 'release');
  if (fs.existsSync(releaseDir)) {
    console.log('[beforePack] Cleaning release directory...');
    try {
      // 尝试删除整个 release 目录（使用 Node.js 的 fs.rmSync，支持 force 选项）
      console.log('[beforePack] Attempting to remove release directory...');
      fs.rmSync(releaseDir, { recursive: true, force: true, maxRetries: 3, retryDelay: 1000 });
      console.log('[beforePack] Successfully removed release directory');
    } catch (error) {
      console.warn(`[beforePack] Could not fully remove release directory: ${error.message}`);
      // 如果整体删除失败，尝试删除 venv 目录
      try {
        const releaseWinUnpacked = path.join(releaseDir, 'win-unpacked');
        if (fs.existsSync(releaseWinUnpacked)) {
          const venvDir = path.join(releaseWinUnpacked, 'resources', 'venv');
          if (fs.existsSync(venvDir)) {
            console.log('[beforePack] Attempting to remove venv directory...');
            fs.rmSync(venvDir, { recursive: true, force: true, maxRetries: 3, retryDelay: 1000 });
            console.log('[beforePack] Successfully removed venv directory');
          }
        }
      } catch (venvError) {
        console.warn(`[beforePack] Could not remove venv directory: ${venvError.message}`);
        console.warn('[beforePack] You may need to manually delete the release directory');
      }
    }
  }
  
  if (platform === 'win32' || platform === 'windows') {
    // 获取 Electron 版本
    const electronVersion = packager.config.electronVersion || '33.4.11';
    const electronZipPath = path.join(
      process.env.LOCALAPPDATA || process.env.APPDATA,
      'electron',
      'Cache',
      `electron-v${electronVersion}-win32-x64.zip`
    );
    
    // 临时解压目录
    const tempUnpackDir = path.join(packager.projectDir, 'temp-electron-unpack');
    const electronExePath = path.join(tempUnpackDir, 'electron.exe');
    
    console.log(`[beforePack] Preparing to extract Electron from: ${electronZipPath}`);
    
    if (fs.existsSync(electronZipPath)) {
      try {
        // 创建临时解压目录
        if (!fs.existsSync(tempUnpackDir)) {
          fs.mkdirSync(tempUnpackDir, { recursive: true });
        }
        
        // 解压 Electron zip 文件
        console.log(`[beforePack] Extracting Electron zip...`);
        await extract(electronZipPath, { dir: tempUnpackDir });
        
        if (fs.existsSync(electronExePath)) {
          console.log(`[beforePack] Successfully extracted electron.exe`);
          // 将 electron.exe 复制到 node_modules/electron/dist/electron.exe（如果存在）
          const electronDistPath = path.join(packager.projectDir, 'node_modules', 'electron', 'dist', 'electron.exe');
          if (fs.existsSync(path.dirname(electronDistPath))) {
            fs.copyFileSync(electronExePath, electronDistPath);
            console.log(`[beforePack] Copied electron.exe to ${electronDistPath}`);
          }
        } else {
          console.warn(`[beforePack] electron.exe not found in extracted zip`);
        }
      } catch (error) {
        console.error(`[beforePack] Error extracting Electron: ${error.message}`);
      } finally {
        // 清理临时目录
        if (fs.existsSync(tempUnpackDir)) {
          fs.rmSync(tempUnpackDir, { recursive: true, force: true });
        }
      }
    } else {
      console.warn(`[beforePack] Electron zip file not found at: ${electronZipPath}`);
    }
  }
};
