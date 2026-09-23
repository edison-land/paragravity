import React, { useState } from "react"
import { motion } from "framer-motion"
import { Play, Square, Trash2, Mail, Copy, Check } from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "./ui/card"
import { Badge } from "./ui/badge"
import { Button } from "./ui/button"
import type { Profile } from "../types"

interface ProfileCardProps {
  profile: Profile
  onLaunch: (name: string) => Promise<void>
  onStop: (name: string) => Promise<void>
  onDelete: (name: string) => void
}

export const ProfileCard: React.FC<ProfileCardProps> = ({
  profile,
  onLaunch,
  onStop,
  onDelete,
}) => {
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const isRunning = profile.status === "running"

  const handleLaunch = async () => {
    try {
      setLoading(true)
      await onLaunch(profile.name)
    } finally {
      setLoading(false)
    }
  }

  const handleStop = async () => {
    try {
      setLoading(true)
      await onStop(profile.name)
    } finally {
      setLoading(false)
    }
  }

  const handleCopyPath = () => {
    navigator.clipboard.writeText(profile.path)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const initials = profile.name.slice(0, 2).toUpperCase()

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      whileHover={{ y: -3 }}
      transition={{ duration: 0.25 }}
    >
      <Card className={`overflow-hidden transition-all duration-300 ${
        isRunning 
          ? "border-indigo-200/90 shadow-md shadow-indigo-100/50 ring-1 ring-indigo-500/10" 
          : "hover:border-slate-300 hover:shadow-md"
      }`}>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-3">
            
            {/* Avatar & Title */}
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-xs tracking-wider transition-colors shadow-2xs ${
                isRunning
                  ? "bg-gradient-to-tr from-indigo-600 to-purple-600 text-white shadow-indigo-200"
                  : "bg-slate-100 text-slate-700 border border-slate-200"
              }`}>
                {initials}
              </div>
              
              <div>
                <div className="flex items-center gap-2">
                  <CardTitle className="text-base font-extrabold text-[#1E1B4B]">
                    {profile.name}
                  </CardTitle>
                  
                  {isRunning ? (
                    <Badge variant="success" className="gap-1.5 font-mono text-[10px]">
                      <span className="w-1.5 h-1.5 rounded-full pulse-indicator bg-emerald-500 text-emerald-500 inline-block" />
                      PID {profile.pid}
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-[10px] text-slate-400 border-slate-200">
                      ○ 已停止
                    </Badge>
                  )}
                </div>

                <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-1.5">
                  <Mail className="w-3 h-3 text-slate-400 shrink-0" />
                  {profile.email ? (
                    <span className="text-indigo-950 font-semibold">{profile.email}</span>
                  ) : (
                    <span className="text-slate-400 italic">未登录 Google 账号</span>
                  )}
                </div>
              </div>
            </div>

            {/* Storage Size */}
            <span className="text-xs font-mono font-medium text-slate-500 bg-slate-50 border border-slate-100 px-2 py-0.5 rounded-lg">
              {profile.size}
            </span>
          </div>
        </CardHeader>

        <CardContent className="space-y-3 pt-1">
          {/* Description */}
          <p className="text-xs text-slate-600 line-clamp-2 min-h-[32px]">
            {profile.description || "无详细描述信息。"}
          </p>

          {/* Directory & Spotlight info */}
          <div className="flex items-center justify-between p-2 rounded-xl bg-slate-50/80 border border-slate-100 text-[11px]">
            <div className="flex items-center gap-1.5 text-slate-500 font-mono truncate max-w-[240px]">
              <span className="text-slate-400">~</span>
              <span className="truncate">{profile.path.replace(/^\/Users\/[^/]+/, "")}</span>
            </div>
            <button
              onClick={handleCopyPath}
              className="text-slate-400 hover:text-indigo-600 transition-colors p-1"
              title="复制沙盒完整路径"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </CardContent>

        <CardFooter className="pt-3 flex items-center justify-between bg-slate-50/40">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-slate-400 font-medium">Spotlight:</span>
            <span className="text-[10px] font-mono font-semibold text-slate-600 bg-white border border-slate-200 px-1.5 py-0.5 rounded">
              Antigravity ({profile.name})
            </span>
          </div>

          <div className="flex items-center gap-2">
            {isRunning ? (
              <Button
                variant="destructive"
                size="sm"
                onClick={handleStop}
                disabled={loading}
                className="gap-1 px-3"
              >
                <Square className="w-3 h-3 fill-current" />
                <span>停止</span>
              </Button>
            ) : (
              <Button
                variant="default"
                size="sm"
                onClick={handleLaunch}
                disabled={loading}
                className="gap-1 px-3 bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                <Play className="w-3 h-3 fill-current" />
                <span>启动</span>
              </Button>
            )}

            <Button
              variant="ghost"
              size="icon"
              onClick={() => onDelete(profile.name)}
              className="h-8 w-8 text-slate-400 hover:text-rose-600 hover:bg-rose-50"
              title="删除此分身"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </Button>
          </div>
        </CardFooter>
      </Card>
    </motion.div>
  )
}
