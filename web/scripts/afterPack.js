const fs = require('fs');
const path = require('path');
const { extract } = require('extract-zip');

exports.default = async function(context) {
  const { appOutDir, packager } = context;
  const platform = packager.platform.name;
  
  // electron-builder 在 Windows 上可能返回 "windows" 或 "win32"
  if (platform === 'win32' || platform === 'windows') {
    const exePath = path.join(appOutDir, 'electron.exe');
    const newExePath = path.join(appOutDir, 'CodebaseAgent.exe');
    
    // 等待一下确保文件已经创建
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // 如果 electron.exe 不存在，尝试从 zip 文件中解压
    if (!fs.existsSync(exePath)) {
      console.log(`electron.exe not found, attempting to extract from zip...`);
      // 从 packager 对象获取 Electron 版本
      const electronVersion = packager.info?.electronVersion || packager.config?.electronVersion || packager.electronVersion || '33.4.11';
      console.log(`Detected Electron version: ${electronVersion}`);
      const electronZipPath = path.join(
        process.env.LOCALAPPDATA || process.env.APPDATA,
        'electron',
        'Cache',
        `electron-v${electronVersion}-win32-x64.zip`
      );
      
      if (fs.existsSync(electronZipPath)) {
        const tempUnpackDir = path.join(appOutDir, 'temp-electron-unpack');
        try {
          console.log(`Extracting from: ${electronZipPath}`);
          await extract(electronZipPath, { dir: tempUnpackDir });
          
          const extractedExePath = path.join(tempUnpackDir, 'electron.exe');
          if (fs.existsSync(extractedExePath)) {
            fs.copyFileSync(extractedExePath, exePath);
            console.log(`Successfully extracted electron.exe to ${exePath}`);
            // 清理临时目录
            fs.rmSync(tempUnpackDir, { recursive: true, force: true });
          } else {
            console.warn(`electron.exe not found in extracted zip at ${extractedExePath}`);
          }
        } catch (error) {
          console.error(`Failed to extract electron.exe: ${error.message}`);
          if (fs.existsSync(tempUnpackDir)) {
            fs.rmSync(tempUnpackDir, { recursive: true, force: true });
          }
        }
      } else {
        console.warn(`Electron zip file not found at: ${electronZipPath}`);
      }
    }
    
    // 先删除可能存在的旧文件（如果存在）
    if (fs.existsSync(newExePath)) {
      try {
        // 尝试删除旧文件
        fs.unlinkSync(newExePath);
        console.log(`Removed existing ${newExePath}`);
        // 等待一下确保文件删除完成
        await new Promise(resolve => setTimeout(resolve, 500));
      } catch (error) {
        console.warn(`Could not remove existing ${newExePath}: ${error.message}`);
        // 如果删除失败，尝试重命名旧文件
        try {
          const oldBackupPath = newExePath + '.old';
          if (fs.existsSync(oldBackupPath)) {
            fs.unlinkSync(oldBackupPath);
          }
          fs.renameSync(newExePath, oldBackupPath);
          console.log(`Renamed existing ${newExePath} to ${oldBackupPath}`);
        } catch (renameError) {
          console.warn(`Could not rename existing file: ${renameError.message}`);
        }
      }
    }
    
    // 现在尝试重命名
    if (fs.existsSync(exePath)) {
      try {
        fs.renameSync(exePath, newExePath);
        console.log(`Renamed ${exePath} to ${newExePath}`);
      } catch (error) {
        console.error(`Failed to rename executable: ${error.message}`);
        // 如果重命名失败，尝试复制然后删除
        try {
          fs.copyFileSync(exePath, newExePath);
          fs.unlinkSync(exePath);
          console.log(`Copied and removed ${exePath} to ${newExePath}`);
        } catch (copyError) {
          console.error(`Failed to copy executable: ${copyError.message}`);
        }
      }
    } else {
      console.error(`electron.exe still not found at ${exePath} after extraction attempt`);
    }
  }
};
