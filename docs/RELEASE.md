# Release Guide

这个项目建议采用“源码仓库 + GitHub Releases 绿色版”的发布方式。

## 源码仓库应该包含

- `api.py`
- `src/`
- `tests/`
- `docs/`
- `scripts/`
- `start.bat`
- `package.json`
- `requirements.txt`

## 源码仓库不应该包含

- `node_modules/`
- `runtime/`
- `dist/`
- `release-output/`

这些内容要么体积太大，要么属于构建产物或发布产物。

## 绿色版打包方法

先在源码目录执行：

```bash
npm run build
npm run package:green
```

打包脚本会自动生成：

```text
release-output/
├── windows-green/
│   ├── api.py
│   ├── dist/
│   ├── runtime/
│   ├── start.bat
│   └── README-green.md
└── bilibili-video-downloader-windows-green.zip
```

## 上传到 GitHub Releases

建议把 `release-output/bilibili-video-downloader-windows-green.zip` 上传为 Release 附件。

## 推荐发布顺序

1. 推送源码仓库
2. 创建 GitHub Release
3. 上传绿色版 zip
