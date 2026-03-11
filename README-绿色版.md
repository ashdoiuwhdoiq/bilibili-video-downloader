# Bilibili Video Downloader 绿色版

绿色版用于“下载后直接双击运行”。

## 使用方法

1. 解压整个压缩包
2. 确认同级目录下存在 `runtime/`、`dist/`、`api.py`、`start.bat`
3. 双击 `start.bat`
4. 等待本地服务启动后，在浏览器打开 [http://localhost:5000](http://localhost:5000)

## 包内文件说明

```text
runtime/           内嵌 Python 运行时
dist/              前端构建产物
api.py             后端服务入口
start.bat          Windows 启动脚本
README-绿色版.md    当前说明文件
```

## 常见问题

### 双击后提示找不到 `runtime\python.exe`

说明你下载的是源码仓库，而不是绿色版压缩包。请改为下载 GitHub Releases 中的 zip。

### 获取视频信息时报 412

先在同一台电脑的 Chrome / Edge / Firefox 中打开目标视频页并刷新，再回到程序重试。

## 注意事项

- 下载文件默认保存在系统临时目录
- 仅供个人学习交流使用，请遵守相关法律法规
