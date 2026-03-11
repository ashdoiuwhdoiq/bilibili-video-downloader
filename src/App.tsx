import { useEffect, useRef, useState } from 'react'

import './App.css'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { CheckCircle, Download, Film, Gauge, Link2, Loader2, Music, Timer, Video, X } from 'lucide-react'
import { toast } from 'sonner'

import { formatBytes, formatProgressStatus, formatSpeed } from '@/lib/download-progress'
import { getApiBaseUrl, getSelectableFormats, normalizeSelectedFormat, type DownloadType, type VideoFormat } from '@/lib/download-options'

interface VideoInfo {
  title: string
  thumbnail: string
  duration: number
  uploader: string
  formats: VideoFormat[]
  audio_formats: VideoFormat[]
}

interface DownloadTaskProgress {
  task_id: string
  status: string
  progress: number
  speed_text: string
  downloaded_text: string
  total_text: string
  eta_text: string
  message: string
  error: string
  filename: string
  cancel_requested: boolean
}

function App() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null)
  const [selectedResolution, setSelectedResolution] = useState('')
  const [downloadType, setDownloadType] = useState<DownloadType>('both')
  const [taskId, setTaskId] = useState('')
  const [taskProgress, setTaskProgress] = useState<DownloadTaskProgress | null>(null)
  const completedTaskIdRef = useRef('')
  const apiBaseUrl = getApiBaseUrl()
  const selectableFormats = videoInfo ? getSelectableFormats(videoInfo.formats, downloadType) : []

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const resetTaskState = () => {
    setTaskId('')
    setTaskProgress(null)
    completedTaskIdRef.current = ''
  }

  const fetchVideoInfo = async () => {
    if (!url.trim()) return toast.error('请输入 B 站视频链接')
    if (!url.includes('bilibili.com') && !url.includes('b23.tv')) return toast.error('请输入有效的 B 站视频链接')

    setLoading(true)
    try {
      const response = await fetch(`${apiBaseUrl}/api/video-info`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      })
      const data = await response.json()
      if (!response.ok) return toast.error(data.error || '获取视频信息失败')

      resetTaskState()
      setVideoInfo(data)
      setDownloadType('both')
      setSelectedResolution(normalizeSelectedFormat(data.formats, 'both', ''))
      toast.success('获取视频信息成功')
    } catch {
      toast.error('网络错误，请检查后端服务是否启动')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!videoInfo) return
    setSelectedResolution((currentSelection) => normalizeSelectedFormat(videoInfo.formats, downloadType, currentSelection))
  }, [downloadType, videoInfo])

  useEffect(() => {
    if (!taskId) return
    const eventSource = new EventSource(`${apiBaseUrl}/api/download-tasks/${taskId}/events`)

    eventSource.onmessage = (event) => {
      const payload = JSON.parse(event.data) as DownloadTaskProgress
      setTaskProgress(payload)

      if (payload.status === 'error') {
        setDownloading(false)
        toast.error(payload.error || '下载失败')
        eventSource.close()
      }

      if (payload.status === 'cancelled') {
        setDownloading(false)
        toast.info('下载已取消')
        eventSource.close()
      }

      if (payload.status === 'finished' && completedTaskIdRef.current !== payload.task_id) {
        completedTaskIdRef.current = payload.task_id
        void (async () => {
          try {
            const response = await fetch(`${apiBaseUrl}/api/download-tasks/${payload.task_id}/file`)
            if (!response.ok) {
              const data = await response.json()
              throw new Error(data.error || '文件尚未就绪')
            }
            const blob = await response.blob()
            const downloadUrl = window.URL.createObjectURL(blob)
            const anchor = document.createElement('a')
            const ext = downloadType === 'audio' ? 'm4a' : 'mp4'
            const suffix = downloadType === 'video' ? '_video' : downloadType === 'audio' ? '_audio' : ''
            anchor.href = downloadUrl
            anchor.download = `${videoInfo?.title ?? 'download'}${suffix}.${ext}`
            document.body.appendChild(anchor)
            anchor.click()
            document.body.removeChild(anchor)
            window.URL.revokeObjectURL(downloadUrl)
            toast.success('下载完成')
          } catch (error) {
            toast.error(error instanceof Error ? error.message : '下载失败')
          } finally {
            setDownloading(false)
            eventSource.close()
          }
        })()
      }
    }

    eventSource.onerror = () => eventSource.close()
    return () => eventSource.close()
  }, [apiBaseUrl, downloadType, taskId, videoInfo?.title])

  const handleDownload = async () => {
    if (!videoInfo) return
    setDownloading(true)
    completedTaskIdRef.current = ''
    setTaskProgress({
      task_id: '',
      status: 'queued',
      progress: 0,
      speed_text: '--',
      downloaded_text: '0 B',
      total_text: '--',
      eta_text: '--',
      message: '等待开始',
      error: '',
      filename: '',
      cancel_requested: false,
    })

    try {
      const response = await fetch(`${apiBaseUrl}/api/download-tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, format_id: downloadType === 'audio' ? '' : selectedResolution, type: downloadType }),
      })
      const data = await response.json()
      if (!response.ok) {
        setDownloading(false)
        return toast.error(data.error || '创建下载任务失败')
      }
      setTaskId(data.task_id)
      toast.info('下载任务已创建')
    } catch {
      setDownloading(false)
      toast.error('下载出错，请重试')
    }
  }

  const handleCancel = async () => {
    if (!taskId) return
    try {
      const response = await fetch(`${apiBaseUrl}/api/download-tasks/${taskId}/cancel`, { method: 'POST' })
      const data = await response.json()
      if (!response.ok) return toast.error(data.error || '取消失败')
      setTaskProgress((current) => current ? { ...current, status: 'cancelled', message: '已取消', cancel_requested: true } : current)
    } catch {
      toast.error('取消失败，请重试')
    }
  }

  const canCancel = downloading && taskProgress && !['finished', 'error', 'cancelled'].includes(taskProgress.status)

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 via-white to-blue-50">
      <header className="sticky top-0 z-50 border-b border-pink-100 bg-white/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-pink-500 to-pink-600 shadow-lg shadow-pink-200">
              <Download className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="bg-gradient-to-r from-pink-600 to-pink-500 bg-clip-text text-xl font-bold text-transparent">B 站视频下载器</h1>
              <p className="text-xs text-gray-500">简单、快速、免安装</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <CheckCircle className="h-4 w-4 text-green-500" />
            <span>支持高清视频下载</span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-12">
        <Card className="border-0 bg-white/90 shadow-2xl shadow-pink-100/50 backdrop-blur-sm">
          <CardContent className="p-8">
            <div className="mb-8 text-center">
              <h2 className="mb-2 text-2xl font-bold text-gray-800">粘贴 B 站视频链接</h2>
              <p className="text-gray-500">支持 BV、AV 和短链接等多种格式</p>
            </div>
            <div className="flex gap-3">
              <div className="relative flex-1">
                <Link2 className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <Input placeholder="https://www.bilibili.com/video/BV..." value={url} onChange={(event) => setUrl(event.target.value)} className="h-14 rounded-xl border-2 border-gray-200 pl-12 text-lg transition-all focus:border-pink-400 focus:ring-pink-200" onKeyDown={(event) => event.key === 'Enter' && fetchVideoInfo()} />
              </div>
              <Button onClick={fetchVideoInfo} disabled={loading} className="h-14 rounded-xl bg-gradient-to-r from-pink-500 to-pink-600 px-8 text-white shadow-lg shadow-pink-200 transition-all hover:from-pink-600 hover:to-pink-700 hover:shadow-xl hover:shadow-pink-300">
                {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <><Film className="mr-2 h-5 w-5" />获取信息</>}
              </Button>
            </div>
          </CardContent>
        </Card>

        {videoInfo && (
          <Card className="mt-8 overflow-hidden border-0 bg-white/90 shadow-2xl shadow-blue-100/50 backdrop-blur-sm animate-in slide-in-from-bottom-4 duration-500">
            <CardHeader className="border-b border-gray-100 bg-gradient-to-r from-blue-50 to-pink-50">
              <CardTitle className="text-lg text-gray-800">视频信息</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="flex gap-6">
                <div className="w-48 flex-shrink-0">
                  <div className="relative aspect-video overflow-hidden rounded-xl bg-gray-100 shadow-lg">
                    {videoInfo.thumbnail ? <img src={`${apiBaseUrl}/api/thumbnail?url=${encodeURIComponent(videoInfo.thumbnail)}`} alt={videoInfo.title} className="h-full w-full object-cover" onError={(event) => { ;(event.target as HTMLImageElement).src = videoInfo.thumbnail }} /> : <div className="flex h-full w-full items-center justify-center text-gray-400"><Film className="h-12 w-12" /></div>}
                    <div className="absolute bottom-2 right-2 rounded bg-black/70 px-2 py-1 text-xs text-white">{formatDuration(videoInfo.duration)}</div>
                  </div>
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="mb-2 line-clamp-2 text-lg font-bold text-gray-800" title={videoInfo.title}>{videoInfo.title}</h3>
                  <p className="mb-4 text-sm text-gray-500">UP 主: {videoInfo.uploader}</p>
                  <div className="space-y-4">
                    <div>
                      <Label className="mb-2 block text-sm font-medium text-gray-700">下载类型</Label>
                      <RadioGroup value={downloadType} onValueChange={(value) => setDownloadType(value as DownloadType)} className="flex gap-4">
                        <div className="flex items-center space-x-2"><RadioGroupItem value="both" id="both" /><Label htmlFor="both" className="flex cursor-pointer items-center gap-1"><Video className="h-4 w-4" />视频+音频</Label></div>
                        <div className="flex items-center space-x-2"><RadioGroupItem value="video" id="video" /><Label htmlFor="video" className="flex cursor-pointer items-center gap-1"><Film className="h-4 w-4" />仅视频</Label></div>
                        <div className="flex items-center space-x-2"><RadioGroupItem value="audio" id="audio" /><Label htmlFor="audio" className="flex cursor-pointer items-center gap-1"><Music className="h-4 w-4" />仅音频</Label></div>
                      </RadioGroup>
                    </div>
                    {downloadType !== 'audio' && (
                      <div>
                        <Label className="mb-2 block text-sm font-medium text-gray-700">选择分辨率</Label>
                        <Select value={selectedResolution} onValueChange={setSelectedResolution}>
                          <SelectTrigger className="w-full max-w-xs"><SelectValue placeholder="选择分辨率" /></SelectTrigger>
                          <SelectContent>{selectableFormats.map((format) => <SelectItem key={format.format_id} value={format.format_id}>{format.resolution} ({format.ext})</SelectItem>)}</SelectContent>
                        </Select>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {taskProgress && (
                <div className="mt-6 rounded-2xl border border-pink-100 bg-gradient-to-r from-white to-pink-50 p-4">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-gray-800">{taskProgress.message || formatProgressStatus(taskProgress.status)}</p>
                      <p className="text-xs text-gray-500">{taskProgress.progress}% · {taskProgress.downloaded_text} / {taskProgress.total_text}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="rounded-full bg-pink-100 px-3 py-1 text-xs font-medium text-pink-700">{formatProgressStatus(taskProgress.status)}</span>
                      {canCancel && <Button type="button" variant="outline" onClick={handleCancel} className="h-8 rounded-full border-red-200 px-3 text-red-600 hover:bg-red-50 hover:text-red-700"><X className="mr-1 h-3.5 w-3.5" />取消</Button>}
                    </div>
                  </div>
                  <div className="h-3 overflow-hidden rounded-full bg-pink-100"><div className="h-full rounded-full bg-gradient-to-r from-pink-500 to-pink-600 transition-all duration-300" style={{ width: `${taskProgress.progress}%` }} /></div>
                  <div className="mt-3 grid grid-cols-3 gap-3 text-sm text-gray-600">
                    <div className="rounded-xl bg-white/80 p-3"><div className="mb-1 flex items-center gap-2 text-xs text-gray-400"><Gauge className="h-3.5 w-3.5" />当前速率</div><div className="font-medium text-gray-800">{taskProgress.speed_text || formatSpeed(undefined)}</div></div>
                    <div className="rounded-xl bg-white/80 p-3"><div className="mb-1 flex items-center gap-2 text-xs text-gray-400"><Timer className="h-3.5 w-3.5" />剩余时间</div><div className="font-medium text-gray-800">{taskProgress.eta_text || '--'}</div></div>
                    <div className="rounded-xl bg-white/80 p-3"><div className="mb-1 flex items-center gap-2 text-xs text-gray-400"><Download className="h-3.5 w-3.5" />已下载</div><div className="font-medium text-gray-800">{taskProgress.downloaded_text || formatBytes(undefined)}</div></div>
                  </div>
                  {taskProgress.error && <p className="mt-3 text-sm text-red-600">{taskProgress.error}</p>}
                </div>
              )}

              <div className="mt-6 border-t border-gray-100 pt-6">
                <Button onClick={handleDownload} disabled={downloading || (downloadType !== 'audio' && !selectedResolution)} className="h-12 w-full rounded-xl bg-gradient-to-r from-pink-500 to-pink-600 text-white shadow-lg shadow-pink-200 transition-all hover:from-pink-600 hover:to-pink-700 hover:shadow-xl hover:shadow-pink-300">
                  {downloading ? <><Loader2 className="mr-2 h-5 w-5 animate-spin" />下载中...</> : <><Download className="mr-2 h-5 w-5" />开始下载{downloadType === 'audio' ? '音频' : '视频'}</>}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  )
}

export default App
