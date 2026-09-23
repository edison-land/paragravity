import React from "react"
import { motion } from "framer-motion"
import { Sparkles, Command, RefreshCw } from "lucide-react"
import { Button } from "./ui/button"

interface NavbarProps {
  onRefresh: () => void
  isRefreshing: boolean
}

export const Navbar: React.FC<NavbarProps> = ({ onRefresh, isRefreshing }) => {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-indigo-100/80 bg-white/80 backdrop-blur-md">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        
        {/* Brand Logo & Name */}
        <div className="flex items-center gap-3">
          <motion.div 
            whileHover={{ rotate: 15, scale: 1.05 }}
            className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-md shadow-indigo-200"
          >
            <span className="text-xl">🌌</span>
          </motion.div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-extrabold text-[#1E1B4B] tracking-tight">
                ParaGravity
              </h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                v1.0.0
              </span>
            </div>
            <p className="text-[11px] text-slate-500 flex items-center gap-1 font-medium">
              <span>Google Antigravity 并行多账号沙盒控制台</span>
            </p>
          </div>
        </div>

        {/* Action Controls & Spotlight Tip */}
        <div className="flex items-center gap-2.5">
          {/* Spotlight Tip */}
          <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200/80 text-[11px] text-slate-600">
            <Command className="w-3.5 h-3.5 text-indigo-500" />
            <span>Spotlight 快捷启动:</span>
            <kbd className="px-1.5 py-0.5 rounded bg-white border border-slate-200 font-mono text-[10px] shadow-2xs font-semibold text-slate-800">
              Cmd + Space
            </kbd>
          </div>

          {/* Theme Indicator */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-indigo-50/60 border border-indigo-100 text-[11px] text-indigo-700 font-medium">
            <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
            <span>晨曦紫霞白</span>
          </div>

          {/* Refresh Button */}
          <Button 
            variant="outline" 
            size="sm" 
            onClick={onRefresh}
            disabled={isRefreshing}
            className="gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-indigo-600' : 'text-slate-500'}`} />
            <span className="hidden sm:inline">刷新</span>
          </Button>

          {/* GitHub link */}
          <a
            href="https://github.com/edison-land/paragravity"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 rounded-xl text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
            title="GitHub Repository"
          >
            <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
              <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
            </svg>
          </a>
        </div>

      </div>
    </header>
  )
}
