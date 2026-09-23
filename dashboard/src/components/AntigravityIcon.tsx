import { FC } from "react"

interface AntigravityIconProps {
  className?: string
  size?: number
}

export const AntigravityIcon: FC<AntigravityIconProps> = ({ className = "w-7 h-7", size = 28 }) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <defs>
        {/* Antigravity Wave Signature Vertical Gradient: Top Coral Red -> Amber -> Aurora Green -> Sky Blue -> Deep Blue */}
        <linearGradient id="agyIconGradient" x1="50%" y1="10%" x2="50%" y2="85%">
          <stop offset="0%" stopColor="#FF4A2A" />
          <stop offset="25%" stopColor="#F97316" />
          <stop offset="42%" stopColor="#FBBF24" />
          <stop offset="58%" stopColor="#10B981" />
          <stop offset="78%" stopColor="#38BDF8" />
          <stop offset="100%" stopColor="#2563EB" />
        </linearGradient>
      </defs>

      {/* Characteristic Bell Curve / Gravity Wave Arch */}
      <path
        d="M 12 80 
           C 20 78, 25 70, 31 52 
           C 37 32, 43 18, 50 18 
           C 57 18, 63 32, 69 52 
           C 75 70, 80 78, 88 80 
           C 79 81, 71 74, 63 60 
           C 58 52, 54 50, 50 50 
           C 46 50, 42 52, 37 60 
           C 29 74, 21 81, 12 80 Z"
        fill="url(#agyIconGradient)"
      />
    </svg>
  )
}
