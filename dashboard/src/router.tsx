import { useState, useEffect } from "react"
import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
} from "@tanstack/react-router"
import { motion, AnimatePresence } from "framer-motion"
import {
  Clapperboard,
  Volume2,
  VolumeX,
  ChevronUp,
  ChevronDown,
  Columns2,
  Maximize2,
  Zap,
  Play,
  Square,
  Plus,
  Trash2,
  Sparkles,
  LayoutGrid,
  Grid2X2,
  Rows3,
  Layers,
  AppWindow,
  RotateCw,
  Check,
  Copy,
} from "lucide-react"
import { AntigravityIcon } from "./components/AntigravityIcon"
import { CreateProfileDialog } from "./components/CreateProfileDialog"
import { DeleteConfirmDialog } from "./components/DeleteConfirmDialog"
import type { Profile } from "./types"

// Default 4 mock profiles showcasing multi-instance parallelism (2, 3, 4 parallel)
const INITIAL_DEMO_PROFILES: Profile[] = [
  {
    name: "zwe",
    status: "running",
    pid: 49377,
    email: "zwe.dev@gmail.com",
    has_token: true,
    token_exp: null,
    size: "24.5 MB",
    description: "Quota 94% · 主开发环境",
    created_at: new Date().toISOString(),
    path: "~/.antigravity-profiles/zwe",
  },
  {
    name: "research",
    status: "running",
    pid: 50124,
    email: "lab.gemini@company.com",
    has_token: true,
    token_exp: null,
    size: "18.2 MB",
    description: "RAM 18.2 MB · /goal 自治研究员",
    created_at: new Date().toISOString(),
    path: "~/.antigravity-profiles/research",
  },
  {
    name: "evaluator",
    status: "running",
    pid: 51088,
    email: "eval.agent@gmail.com",
    has_token: true,
    token_exp: null,
    size: "22.4 MB",
    description: "RAM 22.4 MB · 矩阵并发评测",
    created_at: new Date().toISOString(),
    path: "~/.antigravity-profiles/evaluator",
  },
  {
    name: "sandbox",
    status: "stopped",
    pid: 0,
    email: "sandbox.test@gmail.com",
    has_token: false,
    token_exp: null,
    size: "15.1 MB",
    description: "纯净隔离新沙盒",
    created_at: new Date().toISOString(),
    path: "~/.antigravity-profiles/sandbox",
  },
]

interface ChromaTheme {
  name: string
  avatarBg: string
  avatarText: string
  activeBorder: string
  idleBorder: string
  tagColor: string
  metricColor: string
  badgeDot: string
  label: string
}

const CHROMA_THEMES: ChromaTheme[] = [
  {
    name: "sky",
    avatarBg: "bg-sky-500",
    avatarText: "text-white",
    activeBorder: "border-sky-400 shadow-card-blue ring-1 ring-sky-400/30",
    idleBorder: "border-sky-200/80 hover:border-sky-300",
    tagColor: "text-sky-700 bg-sky-50 border-sky-200",
    metricColor: "text-sky-600",
    badgeDot: "bg-sky-500",
    label: "蔚蓝",
  },
  {
    name: "coral",
    avatarBg: "bg-[#FF5232]",
    avatarText: "text-white",
    activeBorder: "border-rose-400 shadow-card-coral ring-1 ring-rose-400/30",
    idleBorder: "border-rose-200/80 hover:border-rose-300",
    tagColor: "text-rose-700 bg-rose-50 border-rose-200",
    metricColor: "text-[#FF5232]",
    badgeDot: "bg-[#FF5232]",
    label: "珊瑚红",
  },
  {
    name: "emerald",
    avatarBg: "bg-emerald-600",
    avatarText: "text-white",
    activeBorder: "border-emerald-400 shadow-card-emerald ring-1 ring-emerald-400/30",
    idleBorder: "border-emerald-200/80 hover:border-emerald-300",
    tagColor: "text-emerald-700 bg-emerald-50 border-emerald-200",
    metricColor: "text-emerald-600",
    badgeDot: "bg-emerald-500",
    label: "翡翠绿",
  },
  {
    name: "violet",
    avatarBg: "bg-purple-600",
    avatarText: "text-white",
    activeBorder: "border-purple-400 shadow-card-purple ring-1 ring-purple-400/30",
    idleBorder: "border-purple-200/80 hover:border-purple-300",
    tagColor: "text-purple-700 bg-purple-50 border-purple-200",
    metricColor: "text-purple-600",
    badgeDot: "bg-purple-500",
    label: "紫罗兰",
  },
  {
    name: "amber",
    avatarBg: "bg-amber-500",
    avatarText: "text-white",
    activeBorder: "border-amber-400 shadow-card-amber ring-1 ring-amber-400/30",
    idleBorder: "border-amber-200/80 hover:border-amber-300",
    tagColor: "text-amber-700 bg-amber-50 border-amber-200",
    metricColor: "text-amber-600",
    badgeDot: "bg-amber-500",
    label: "琥珀金",
  },
]

type LayoutMode = "auto" | "2-split" | "3-split" | "4-grid" | "stack"

function IslandDashboard() {
  const [realProfiles, setRealProfiles] = useState<Profile[]>([])
  const [isDemoMode, setIsDemoMode] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [layoutMode, setLayoutMode] = useState<LayoutMode>("auto")
  const [activeProfileIndex, setActiveProfileIndex] = useState(0)
  const [selectedProfiles, setSelectedProfiles] = useState<string[]>([])
  const [createOpen, setCreateOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const [isBatchLaunching, setIsBatchLaunching] = useState(false)
  const [copiedName, setCopiedName] = useState<string | null>(null)

  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(null), 3000)
  }

  const fetchProfiles = async () => {
    try {
      const res = await fetch("/api/profiles")
      if (res.ok) {
        const data = await res.json()
        setRealProfiles(data)
        if (data.length === 0 && !isDemoMode) {
          setIsDemoMode(true)
        }
      }
    } catch {
      if (realProfiles.length === 0) {
        setIsDemoMode(true)
      }
    }
  }

  useEffect(() => {
    fetchProfiles()
    const timer = setInterval(fetchProfiles, 3000)
    return () => clearInterval(timer)
  }, [])

  const profilesToDisplay = isDemoMode
    ? INITIAL_DEMO_PROFILES
    : realProfiles.length > 0
    ? realProfiles
    : INITIAL_DEMO_PROFILES

  // Listen to ⌘D (cycle layout) & ⌘Enter (parallel launch)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "d") {
        e.preventDefault()
        setLayoutMode((prev) => {
          const modes: LayoutMode[] = ["auto", "2-split", "3-split", "4-grid", "stack"]
          const nextIdx = (modes.indexOf(prev) + 1) % modes.length
          const next = modes[nextIdx]
          showToast(`切换布局模式: ${next}`)
          return next
        })
      } else if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault()
        handleParallelLaunchAll()
      } else if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "a") {
        e.preventDefault()
        setSelectedProfiles((prev) =>
          prev.length === profilesToDisplay.length ? [] : profilesToDisplay.map((p) => p.name)
        )
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [profilesToDisplay, layoutMode])

  const toggleSelectProfile = (name: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    setSelectedProfiles((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]
    )
  }

  const handleLaunch = async (name: string) => {
    if (isDemoMode) {
      showToast(`[演示] 分身 '${name}' 实例已就绪`)
      return
    }
    try {
      const res = await fetch(`/api/profiles/${encodeURIComponent(name)}/launch`, { method: "POST" })
      if (res.ok) {
        showToast(`分身 '${name}' 启动成功！`)
        fetchProfiles()
      } else {
        const err = await res.json()
        showToast(`启动失败: ${err.error || "未知错误"}`)
      }
    } catch (err: any) {
      showToast(`错误: ${err.message}`)
    }
  }

  const handleStop = async (name: string) => {
    if (isDemoMode) {
      showToast(`[演示] 分身 '${name}' 已停止`)
      return
    }
    try {
      const res = await fetch(`/api/profiles/${encodeURIComponent(name)}/stop`, { method: "POST" })
      if (res.ok) {
        showToast(`分身 '${name}' 已停止运行`)
        fetchProfiles()
      }
    } catch (err: any) {
      showToast(`错误: ${err.message}`)
    }
  }

  // Parallel Launch All (or selected)
  const handleParallelLaunchAll = async () => {
    const targets =
      selectedProfiles.length > 0
        ? selectedProfiles
        : profilesToDisplay.map((p) => p.name)

    if (isDemoMode) {
      showToast(`[演示] 已同时并行唤起 ${targets.length} 个实例！`)
      return
    }

    try {
      setIsBatchLaunching(true)
      showToast(`正在同时并行唤起 ${targets.length} 个 Antigravity 窗口...`)
      const res = await fetch("/api/batch/launch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ names: targets }),
      })
      if (res.ok) {
        showToast(`🎉 成功并行启动 ${targets.length} 个环境！`)
        fetchProfiles()
      } else {
        const err = await res.json()
        showToast(`并行启动出现问题: ${err.error || "请重试"}`)
      }
    } catch (err: any) {
      showToast(`启动出错: ${err.message}`)
    } finally {
      setIsBatchLaunching(false)
    }
  }

  // Stop All Running
  const handleStopAll = async () => {
    const runningNames = profilesToDisplay
      .filter((p) => p.status === "running")
      .map((p) => p.name)

    if (runningNames.length === 0) {
      showToast("当前没有正在运行的实例")
      return
    }

    if (isDemoMode) {
      showToast("[演示] 所有运行中实例已全部休眠")
      return
    }

    try {
      showToast(`正在批量休眠 ${runningNames.length} 个实例...`)
      const res = await fetch("/api/batch/stop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ names: runningNames }),
      })
      if (res.ok) {
        showToast("已成功全部停止")
        fetchProfiles()
      }
    } catch (err: any) {
      showToast(`停止出错: ${err.message}`)
    }
  }

  // Tile Windows on macOS Display
  const handleTileWindows = async () => {
    if (isDemoMode) {
      showToast("[演示] 已自动按四宫格/多列将窗口智能平铺到屏幕！")
      return
    }

    try {
      showToast("正在自动检测窗口并在屏幕上智能平铺...")
      const res = await fetch("/api/tile", { method: "POST" })
      const data = await res.json()
      if (data.success) {
        showToast("🪟 屏幕窗口平铺完成！")
      } else {
        showToast(`平铺提示: ${data.error || data.message || "请检查辅助功能权限"}`)
      }
    } catch (err: any) {
      showToast(`平铺失败: ${err.message}`)
    }
  }

  const handleCreate = async (name: string, description: string, launch: boolean) => {
    if (isDemoMode) {
      setIsDemoMode(false)
    }
    const res = await fetch("/api/profiles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description, launch }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.error || "创建失败")
    }
    showToast(`分身 '${name}' 创建成功！`)
    fetchProfiles()
  }

  const handleDelete = async (name: string) => {
    const res = await fetch(`/api/profiles/${encodeURIComponent(name)}`, { method: "DELETE" })
    if (res.ok) {
      showToast(`分身 '${name}' 已完全删除`)
      fetchProfiles()
    }
  }

  const handleCopyEmail = (email: string, e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(email)
    setCopiedName(email)
    setTimeout(() => setCopiedName(null), 1800)
    showToast(`已复制: ${email}`)
  }

  // Calculate Grid Classes based on layout mode
  const getGridClasses = () => {
    if (layoutMode === "stack") return "grid-cols-1 max-w-xl mx-auto"
    if (layoutMode === "2-split") return "grid-cols-1 md:grid-cols-2"
    if (layoutMode === "3-split") return "grid-cols-1 md:grid-cols-3"
    if (layoutMode === "4-grid") return "grid-cols-1 sm:grid-cols-2"

    // Auto Mode:
    const count = profilesToDisplay.length
    if (count <= 1) return "grid-cols-1 max-w-md mx-auto"
    if (count === 2) return "grid-cols-1 md:grid-cols-2"
    if (count === 3) return "grid-cols-1 md:grid-cols-3"
    if (count === 4) return "grid-cols-1 sm:grid-cols-2"
    return "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
  }

  // Calculate container max width
  const getContainerMaxWidth = () => {
    if (layoutMode === "3-split" || (layoutMode === "auto" && profilesToDisplay.length === 3)) {
      return "max-w-[1040px]"
    }
    if (layoutMode === "4-grid" || (layoutMode === "auto" && profilesToDisplay.length >= 4)) {
      return "max-w-[960px]"
    }
    return "max-w-[860px]"
  }

  const runningCount = profilesToDisplay.filter((p) => p.status === "running").length

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#0F172A] flex flex-col items-center justify-center p-4 sm:p-8">
      {/* Toast Notification */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-8 z-50 px-4 py-2 rounded-full bg-slate-900 text-white text-xs font-semibold shadow-xl shadow-slate-900/20 flex items-center gap-2 border border-slate-800"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>{toastMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Island Frame Container in Pure White */}
      <motion.div
        layout
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className={`w-full ${getContainerMaxWidth()} bg-white border border-slate-200/90 rounded-[36px] p-6 sm:p-8 shadow-island-white relative overflow-hidden transition-all duration-300`}
      >
        {/* Top Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          {/* Logo with Antigravity Multi-Color Wave Arch */}
          <div className="flex items-center gap-3">
            <motion.div
              whileHover={{ rotate: 10, scale: 1.05 }}
              transition={{ type: "spring", stiffness: 260, damping: 20 }}
              className="w-10 h-10 rounded-2xl bg-white border border-slate-200/90 flex items-center justify-center shadow-md shadow-sky-500/10 cursor-pointer p-1 shrink-0"
            >
              <AntigravityIcon size={28} />
            </motion.div>

            <div>
              <div className="flex items-center gap-2.5">
                <span className="text-xl font-black tracking-tight text-slate-900">
                  ParaGravity
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono bg-sky-50 text-sky-700 border border-sky-200 font-semibold">
                  Multi-Sandbox Matrix
                </span>
              </div>
              <div className="text-xs text-slate-400 font-medium flex items-center gap-2 mt-0.5">
                <span>共 {profilesToDisplay.length} 个独立环境</span>
                <span>•</span>
                <span className={runningCount > 0 ? "text-emerald-600 font-semibold" : "text-slate-400"}>
                  {runningCount} 个正在运行
                </span>
              </div>
            </div>
          </div>

          {/* Right Action Controls: Layout Switcher + Auto-Demo + Mute + Collapse */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* Layout Mode Selector */}
            <div className="flex items-center bg-slate-100 p-1 rounded-full border border-slate-200">
              <button
                onClick={() => setLayoutMode("auto")}
                className={`px-2.5 py-1 rounded-full text-[11px] font-semibold flex items-center gap-1 transition-all ${
                  layoutMode === "auto" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-500 hover:text-slate-800"
                }`}
                title="自动自适应网格"
              >
                <LayoutGrid className="w-3 h-3" />
                <span>自适应</span>
              </button>
              <button
                onClick={() => setLayoutMode("2-split")}
                className={`px-2 py-1 rounded-full text-[11px] font-semibold flex items-center gap-1 transition-all ${
                  layoutMode === "2-split" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-500 hover:text-slate-800"
                }`}
                title="双栏并排 (⌘D)"
              >
                <Columns2 className="w-3 h-3" />
                <span>2栏</span>
              </button>
              <button
                onClick={() => setLayoutMode("3-split")}
                className={`px-2 py-1 rounded-full text-[11px] font-semibold flex items-center gap-1 transition-all ${
                  layoutMode === "3-split" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-500 hover:text-slate-800"
                }`}
                title="三列全景"
              >
                <Rows3 className="w-3 h-3 rotate-90" />
                <span>3列</span>
              </button>
              <button
                onClick={() => setLayoutMode("4-grid")}
                className={`px-2 py-1 rounded-full text-[11px] font-semibold flex items-center gap-1 transition-all ${
                  layoutMode === "4-grid" ? "bg-white text-slate-900 shadow-2xs" : "text-slate-500 hover:text-slate-800"
                }`}
                title="四宫格矩阵"
              >
                <Grid2X2 className="w-3 h-3" />
                <span>4格</span>
              </button>
            </div>

            {/* Auto-Demo Toggle Button */}
            <button
              onClick={() => {
                setIsDemoMode(!isDemoMode)
                showToast(isDemoMode ? "已切换至本地真实环境" : "已开启多实例演示预览 (Auto-Demo)")
              }}
              className={`px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-1.5 transition-all cursor-pointer ${
                isDemoMode
                  ? "bg-sky-50 text-sky-700 border border-sky-300 shadow-xs"
                  : "bg-slate-100/80 text-slate-600 border border-slate-200 hover:text-slate-900 hover:bg-slate-200/60"
              }`}
            >
              <Clapperboard className="w-3.5 h-3.5 text-sky-600" />
              <span>{isDemoMode ? "演示中" : "演示"}</span>
            </button>

            {/* Sound Toggle */}
            <button
              onClick={() => setIsMuted(!isMuted)}
              className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200/80 border border-slate-200 flex items-center justify-center text-slate-500 hover:text-slate-900 transition-colors"
              title={isMuted ? "开启音效" : "静音"}
            >
              {isMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
            </button>

            {/* Collapse / Expand */}
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200/80 border border-slate-200 flex items-center justify-center text-slate-500 hover:text-slate-900 transition-colors"
              title={isCollapsed ? "展开" : "收起"}
            >
              {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Inner Content Area */}
        <AnimatePresence>
          {!isCollapsed && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.25 }}
              className="space-y-4 pt-5"
            >
              {/* Inner Stage (Pure White with Light Ice-Blue Border) */}
              <div className="bg-[#FFFFFF] p-5 sm:p-6 rounded-[28px] border border-slate-200/80 shadow-inner shadow-slate-100/50 relative">
                
                {/* Profile Cards Container (Dynamic Adaptive Grid for 1, 2, 3, 4, N) */}
                <div className={`grid gap-4 ${getGridClasses()}`}>
                  {profilesToDisplay.map((profile, idx) => {
                    const theme = CHROMA_THEMES[idx % CHROMA_THEMES.length]
                    const isFocused = idx === activeProfileIndex
                    const isRunning = profile.status === "running"
                    const isSelected = selectedProfiles.includes(profile.name)

                    return (
                      <div key={profile.name} className="relative">
                        <motion.div
                          onClick={() => setActiveProfileIndex(idx)}
                          whileHover={{ scale: 1.008 }}
                          transition={{ duration: 0.15 }}
                          className={`rounded-[20px] p-5 transition-all duration-300 cursor-pointer relative bg-white border-2 ${
                            isFocused
                              ? theme.activeBorder
                              : theme.idleBorder
                          }`}
                        >
                          {/* Top Row: Avatar + Title & PID + Neon Dot */}
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-3">
                              {/* Square Avatar with Theme Color */}
                              <div
                                className={`w-11 h-11 rounded-xl flex items-center justify-center font-bold text-base shadow-xs ${theme.avatarBg} ${theme.avatarText}`}
                              >
                                {profile.name.charAt(0).toUpperCase()}
                              </div>

                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="text-base font-bold text-slate-900 tracking-tight">
                                    {profile.name}
                                  </span>
                                  {isRunning ? (
                                    <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">
                                      PID {profile.pid}
                                    </span>
                                  ) : (
                                    <span className="text-[11px] font-mono text-slate-400">
                                      已休眠
                                    </span>
                                  )}
                                </div>

                                {/* Email with quick copy */}
                                <div
                                  onClick={(e) => profile.email && handleCopyEmail(profile.email, e)}
                                  className="text-xs font-mono text-slate-500 mt-1 flex items-center gap-1 hover:text-slate-800 transition-colors"
                                  title="点击复制账号"
                                >
                                  <span className="truncate max-w-[140px] sm:max-w-[180px]">
                                    {profile.email || "未绑定 Google 账号"}
                                  </span>
                                  {profile.email && (
                                    copiedName === profile.email ? (
                                      <Check className="w-3 h-3 text-emerald-500 inline" />
                                    ) : (
                                      <Copy className="w-3 h-3 text-slate-400 inline opacity-60 hover:opacity-100" />
                                    )
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Top Right: Status Dot & Selection Checkbox */}
                            <div className="flex items-center gap-2.5">
                              {/* Multi-Select Checkbox */}
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => toggleSelectProfile(profile.name)}
                                onClick={(e) => e.stopPropagation()}
                                className="w-4 h-4 rounded text-sky-600 border-slate-300 focus:ring-sky-500 cursor-pointer"
                                title="选中参与批量操作"
                              />

                              {/* Running / Stopped Indicator */}
                              {isRunning ? (
                                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 neon-dot inline-block" title="运行中" />
                              ) : (
                                <span className="w-2.5 h-2.5 rounded-full bg-slate-300 inline-block" title="已休眠" />
                              )}
                            </div>
                          </div>

                          {/* Description text */}
                          <div className="mt-3 text-xs text-slate-500 line-clamp-1 font-medium">
                            {profile.description || "独立无干扰沙盒环境"}
                          </div>

                          {/* Bottom Row: Metrics & Quick Action Icons */}
                          <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-100">
                            {/* Metric Tag */}
                            <div>
                              <span className={`font-mono text-xs font-bold ${theme.metricColor} flex items-center gap-1`}>
                                <span>{profile.size || "18.2 MB"}</span>
                              </span>
                            </div>

                            {/* Right Action Icons */}
                            <div className="flex items-center gap-2 text-slate-400">
                              {/* Bring to front / Focus */}
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  showToast(`分身 '${profile.name}' 窗口已居中聚焦`)
                                }}
                                className="p-1 hover:text-slate-700 transition-colors"
                                title="聚焦此实例窗口"
                              >
                                <Maximize2 className="w-3.5 h-3.5" />
                              </button>

                              {/* Start / Stop Quick Toggle */}
                              {isRunning ? (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleStop(profile.name)
                                  }}
                                  className="p-1 text-rose-500 hover:text-rose-600 transition-colors"
                                  title="停止实例"
                                >
                                  <Square className="w-3.5 h-3.5 fill-current" />
                                </button>
                              ) : (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleLaunch(profile.name)
                                  }}
                                  className="p-1 text-emerald-600 hover:text-emerald-700 transition-colors"
                                  title="单独启动"
                                >
                                  <Play className="w-3.5 h-3.5 fill-current" />
                                </button>
                              )}

                              {/* Delete button (for real profiles) */}
                              {!isDemoMode && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setDeleteTarget(profile.name)
                                  }}
                                  className="p-1 text-slate-400 hover:text-rose-600 transition-colors"
                                  title="删除配置"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </div>
                          </div>
                        </motion.div>
                      </div>
                    )
                  })}
                </div>

              </div>

              {/* Floating Batch Operation & Controls Dock */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
                {/* Left: Memory Footprint & Shortcut Guide */}
                <div className="flex items-center gap-3 flex-wrap">
                  <div className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-slate-100 border border-slate-200 text-xs font-mono text-slate-700 font-medium">
                    <Zap className="w-3.5 h-3.5 text-amber-500" />
                    <span>0 MB 内存闲置</span>
                  </div>

                  <span className="text-xs text-slate-400 font-medium">
                    • 按 <kbd className="font-mono text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">⌘D</kbd> 切分屏
                    • <kbd className="font-mono text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">⌘Enter</kbd> 一键全开
                  </span>
                </div>

                {/* Right: Actions (Tile + Stop All + Parallel Launch) */}
                <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end flex-wrap">
                  {/* Tile Windows Button */}
                  <button
                    onClick={handleTileWindows}
                    className="px-3 py-2 rounded-xl text-xs font-semibold bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 shadow-2xs flex items-center gap-1.5 transition-all cursor-pointer"
                    title="在屏幕上按四宫格/多列自动平铺摆放所有实例窗口"
                  >
                    <AppWindow className="w-3.5 h-3.5 text-indigo-500" />
                    <span>屏幕智能平铺</span>
                  </button>

                  {/* Stop All Button */}
                  {runningCount > 0 && (
                    <button
                      onClick={handleStopAll}
                      className="px-3 py-2 rounded-xl text-xs font-semibold bg-white hover:bg-rose-50 text-rose-600 border border-rose-200 shadow-2xs flex items-center gap-1.5 transition-all cursor-pointer"
                      title="休眠全部实例"
                    >
                      <Square className="w-3 h-3 fill-current" />
                      <span>全部休眠</span>
                    </button>
                  )}

                  {/* + New Profile Button */}
                  <button
                    onClick={() => setCreateOpen(true)}
                    className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 shadow-2xs flex items-center gap-1.5 transition-all cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5 text-sky-500" />
                    <span>新建分身</span>
                  </button>

                  {/* Main Glowing Button: Cyan-to-Coral Duotone Gradient */}
                  <motion.button
                    whileTap={{ scale: 0.97 }}
                    whileHover={{ scale: 1.02 }}
                    onClick={handleParallelLaunchAll}
                    disabled={isBatchLaunching}
                    className="px-5 py-2.5 rounded-2xl text-xs font-bold text-white gradient-btn-duotone glow-btn-duotone flex items-center gap-2 cursor-pointer transition-all disabled:opacity-70"
                  >
                    {isBatchLaunching ? (
                      <RotateCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Layers className="w-4 h-4" />
                    )}
                    <span>
                      {selectedProfiles.length > 0
                        ? `并行启动选中 (${selectedProfiles.length})`
                        : `并行启动全部 (${profilesToDisplay.length}并联)`}
                    </span>
                    <span className="bg-white/25 px-1.5 py-0.5 rounded text-[10px] font-mono font-normal">
                      ⌘⏎
                    </span>
                  </motion.button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Dialogs */}
      <CreateProfileDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreate={handleCreate}
      />

      <DeleteConfirmDialog
        profileName={deleteTarget}
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  )
}

// TanStack Router Definition
const rootRoute = createRootRoute({
  component: () => <Outlet />,
})

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: IslandDashboard,
})

const routeTree = rootRoute.addChildren([indexRoute])

export const router = createRouter({ routeTree })

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}
