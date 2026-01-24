#!/usr/bin/env node

/**
 * 修复 Electron 打包后的 HTML 文件中的资源路径
 * 将绝对路径改为相对路径，以便在 file:// 协议下正确加载
 */

const fs = require('fs')
const path = require('path')

const distDir = path.join(__dirname, '../dist')
const indexPath = path.join(distDir, 'index.html')

if (!fs.existsSync(indexPath)) {
  console.error('index.html not found:', indexPath)
  process.exit(1)
}

console.log('Fixing paths in index.html for Electron...')

let html = fs.readFileSync(indexPath, 'utf-8')

// 将绝对路径改为相对路径
// /assets/... -> ./assets/...
html = html.replace(/href="\/assets\//g, 'href="./assets/')
html = html.replace(/src="\/assets\//g, 'src="./assets/')
// 处理其他可能的绝对路径
html = html.replace(/href="\//g, 'href="./')
html = html.replace(/src="\//g, 'src="./')

fs.writeFileSync(indexPath, html, 'utf-8')

console.log('✓ Paths fixed in index.html')
