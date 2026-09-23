import { useState, FC, FormEvent } from "react"
import { Sparkles, AlertCircle, CheckCircle2, FolderGit2 } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "./ui/dialog"
import { Button } from "./ui/button"

interface CreateProfileDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreate: (name: string, description: string, launch: boolean) => Promise<void>
}

const NAME_REGEX = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/

export const CreateProfileDialog: FC<CreateProfileDialogProps> = ({
  open,
  onOpenChange,
  onCreate,
}) => {
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [launchImmediately, setLaunchImmediately] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isValidName = name.length > 0 && NAME_REGEX.test(name)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!isValidName) {
      setError("名称必须以字母或数字开头，仅限字母、数字、点(.)、下划线(_)或连字符(-)，长度1-64。")
      return
    }

    try {
      setLoading(true)
      setError(null)
      await onCreate(name, description, launchImmediately)
      setName("")
      setDescription("")
      onOpenChange(false)
    } catch (err: any) {
      setError(err.message || "创建分身失败")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-white border border-slate-200 text-slate-900 shadow-xl">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center border border-sky-100">
              <Sparkles className="w-4 h-4" />
            </div>
            <DialogTitle className="text-slate-900 font-bold">新建 Antigravity 隔离分身</DialogTitle>
          </div>
          <DialogDescription className="text-slate-500 text-xs">
            为 Google Antigravity 创建独立的 Chromium 数据沙盒与隔离 Token。
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          {/* Profile Name */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700">
              分身标识名称 (Profile Name) <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              placeholder="例如: zwe, research, work"
              value={name}
              onChange={(e) => {
                setName(e.target.value.trim())
                setError(null)
              }}
              className="w-full px-3.5 py-2.5 text-xs rounded-xl border border-slate-200 bg-slate-50 text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 transition-all font-mono"
              autoFocus
            />
            {name.length > 0 && (
              <div className="text-[11px] flex items-center gap-1 mt-1">
                {isValidName ? (
                  <span className="text-emerald-600 flex items-center gap-1 font-medium">
                    <CheckCircle2 className="w-3 h-3" /> 名称有效
                  </span>
                ) : (
                  <span className="text-rose-500 flex items-center gap-1 font-medium">
                    <AlertCircle className="w-3 h-3" /> 格式不合法（支持字母、数字、.-_）
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700">
              分身说明 (Description)
            </label>
            <input
              type="text"
              placeholder="例如: /goal 自治、企业研发账号、开发测试"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3.5 py-2.5 text-xs rounded-xl border border-slate-200 bg-slate-50 text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 transition-all"
            />
          </div>

          {/* Real-time Sandbox Preview */}
          <div className="p-3 rounded-xl bg-sky-50/60 border border-sky-100 text-[11px] space-y-1 font-mono text-slate-600">
            <div className="font-sans font-bold text-sky-900 text-xs flex items-center gap-1.5">
              <FolderGit2 className="w-3.5 h-3.5 text-sky-500" />
              <span>物理硬沙盒环境预览：</span>
            </div>
            <div className="truncate text-slate-500">
              📁 数据路径: ~/.antigravity-profiles/{name || "<name>"}
            </div>
            <div className="truncate text-slate-500">
              🍎 Spotlight: ~/Applications/Antigravity ({name || "<name>"}).app
            </div>
          </div>

          {/* Checkbox: Launch immediately */}
          <label className="flex items-center gap-2.5 cursor-pointer pt-1">
            <input
              type="checkbox"
              checked={launchImmediately}
              onChange={(e) => setLaunchImmediately(e.target.checked)}
              className="rounded accent-sky-600 w-4 h-4 cursor-pointer"
            />
            <span className="text-xs text-slate-700 font-medium">
              创建后立即在独立窗口中启动实例
            </span>
          </label>

          {/* Error Message */}
          {error && (
            <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-600 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              disabled={loading}
              className="bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
            >
              取消
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={!isValidName || loading}
              className="bg-sky-500 hover:bg-sky-600 text-white min-w-[90px] shadow-sm shadow-sky-400/20"
            >
              {loading ? "正在创建..." : "立即创建"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
