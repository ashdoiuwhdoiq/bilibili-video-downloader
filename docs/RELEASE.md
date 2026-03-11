# Release Guide

这个项目建议用“源码仓库 + Releases 绿色版”的方式发布。

## 源码仓库应该包含

- `api.py`
- `src/`
- `tests/`
- `docs/`
- `start.bat`
- `package.json`
- `requirements.txt`
- 其他源码和配置文件

## 源码仓库不应包含

- `node_modules/`
- `runtime/`
- `dist/`
- 临时文件

## 制作绿色版

1. 在源码目录执行：

```bash
npm run build
```

2. 准备绿色版目录，至少包含：

```text
api.py
dist/
runtime/
start.bat
README-绿色版.md
```

3. 将该目录压缩为 zip

建议文件名：

```text
bilibili-video-downloader-windows-green.zip
```

4. 上传到 GitHub Release

## 发布顺序

1. 先推送源码仓库
2. 再创建 GitHub Release
3. 上传绿色版 zip 作为 Release 附件
