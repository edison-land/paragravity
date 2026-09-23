import { useState, FC } from "react"
import { AlertTriangle } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "./ui/dialog"
import { Button } from "./ui/button"

interface DeleteConfirmDialogProps {
  profileName: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: (name: string) => Promise<void>
}

export const DeleteConfirmDialog: FC<DeleteConfirmDialogProps> = ({
  profileName,
  open,
  onOpenChange,
  onConfirm,
}) => {
  const [loading, setLoading] = useState(false)

  if (!profileName) return null

  const handleConfirm = async () => {
    try {
      setLoading(true)
      await onConfirm(profileName)
      onOpenChange(false)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-white border border-slate-200 text-slate-900 shadow-xl">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center border border-rose-100">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <DialogTitle className="text-slate-900 font-bold">确认删除分身: {profileName}?</DialogTitle>
          </div>
          <DialogDescription className="text-slate-500 text-xs">
            此操作将彻底删除该分身在本地的数据目录（包括缓存、扩展和登录 Token），并移除 Spotlight 启动项。此操作不可撤销。
          </DialogDescription>
        </DialogHeader>

        <div className="p-3 rounded-xl bg-rose-50/60 border border-rose-100 text-xs text-rose-700">
          ⚠️ 注意：请确保已在 Antigravity 窗口中退出该实例。
        </div>

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
            type="button"
            variant="destructive"
            size="sm"
            onClick={handleConfirm}
            disabled={loading}
            className="bg-[#FF5232] hover:bg-[#E04325] text-white min-w-[80px] shadow-sm shadow-rose-500/20"
          >
            {loading ? "正在删除..." : "确认删除"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
