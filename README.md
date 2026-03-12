# Bilibili Video Downloader

一个本地运行的 B 站视频下载工具，提供可视化界面，支持获取视频信息、选择清晰度、下载视频或音频，并在前端实时显示下载进度。

## 适合怎么使用

- 想直接双击使用：请下载 GitHub Releases 里的“绿色版压缩包”
- 想看源码或自己开发：请克隆当前仓库

这个仓库默认是“源码仓库”，不会把内嵌 Python 运行时和打包产物提交到 Git 历史里。

## 功能

- 支持 BV、AV、`b23.tv` 链接
- 支持 `视频+音频`、`仅视频`、`仅音频`
- 支持分辨率选择
- 支持前端实时显示下载进度、速率、阶段状态
- 支持取消下载
- 支持自动读取本机浏览器 cookies，降低 B 站风控报错概率

## 源码运行

要求：

- Python 3.9+
- Node.js 18+

安装并启动：

```bash
git clone https://github.com/ashdoiuwhdoiq/bilibili-video-downloader.git
cd bilibili-video-downloader

pip install -r requirements.txt
npm install
npm run build
python api.py
```

然后访问 [http://localhost:5000](http://localhost:5000)。

## 绿色版运行

绿色版不从源码仓库直接下载，而是从 Releases 下载压缩包。

压缩包内应包含：

- `api.py`
- `dist/`
- `runtime/`
- `start.bat`
- `README-green.md`

下载后解压，双击 `start.bat` 即可。

## 项目结构

```text
api.py                  Flask 后端与下载任务管理
src/                    React 前端源码
tests/                  Python 测试
docs/                   设计与实现计划文档
start.bat               绿色版启动脚本
requirements.txt        Python 依赖
package.json            前端依赖与脚本
```

## 发布建议

- GitHub 仓库：只放源码
- GitHub Releases：上传绿色版 zip

可以参考 `docs/RELEASE.md` 的打包说明。

## 注意事项

- 部分高画质需要大会员权限
- 下载文件默认保存在系统临时目录
- 仅供个人学习交流使用，请遵守相关法律法规

## 技术栈

- 前端：React + Vite + TypeScript + Tailwind CSS
- 后端：Flask + yt-dlp
- 运行方式：本地 Web UI

## License

MIT
