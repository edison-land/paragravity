import React from "react"
import { motion } from "framer-motion"
import { Users, PlayCircle, HardDrive, ShieldCheck, Plus } from "lucide-react"
import { Button } from "./ui/button"
import type { Profile } from "../types"

interface StatsBarProps {
  profiles: Profile[]
  onCreateOpen: () => void
}

export const StatsBar: React.FC<StatsBarProps> = ({ profiles, onCreateOpen }) => {
  const runningCount = profiles.filter(p => p.status === 'running').length
  const totalCount = profiles.length

  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 p-4 sm:p-5 rounded-2xl bg-white border border-indigo-100 shadow-xs">
      
      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:flex sm:items-center gap-3 sm:gap-6 divide-y-0">
        
        {/* Total Profiles */}
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-600">
            <Users className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] text-slate-500 font-medium">总配置分身</div>
            <div className="text-base font-bold text-[#1E1B4B]">{totalCount} 个</div>
          </div>
        </div>

        <div className="hidden sm:block w-px h-8 bg-slate-200" />

        {/* Running Count */}
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600">
            <PlayCircle className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] text-slate-500 font-medium">实时运行中</div>
            <div className="flex items-center gap-1.5">
              <span className="text-base font-bold text-emerald-600">{runningCount}</span>
              {runningCount > 0 && (
                <span className="w-2 h-2 rounded-full pulse-indicator bg-emerald-500 text-emerald-500" />
              )}
            </div>
          </div>
        </div>

        <div className="hidden sm:block w-px h-8 bg-slate-200" />

        {/* Security & Isolation Status */}
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-purple-50 flex items-center justify-center text-purple-600">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] text-slate-500 font-medium">沙盒隔离机制</div>
            <div className="text-xs font-bold text-[#1E1B4B] flex items-center gap-1">
              <span>Token 文件隔离</span>
            </div>
          </div>
        </div>

        <div className="hidden sm:block w-px h-8 bg-slate-200" />

        {/* Storage footprint */}
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-sky-50 flex items-center justify-center text-sky-600">
            <HardDrive className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[11px] text-slate-500 font-medium">沙盒基目录</div>
            <div className="text-xs font-mono text-slate-700">~/.antigravity-profiles</div>
          </div>
        </div>

      </div>

      {/* CTA Button */}
      <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
        <Button 
          onClick={onCreateOpen}
          className="w-full sm:w-auto bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-semibold shadow-md shadow-indigo-100 px-5 py-2.5 gap-2"
        >
          <Plus className="w-4 h-4" />
          <span>新建隔离分身</span>
        </Button>
      </motion.div>

    </div>
  )
}
