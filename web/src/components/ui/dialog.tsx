import * as React from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

interface DialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: React.ReactNode
}

interface DialogContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

const Dialog = ({ open, onOpenChange, children }: DialogProps) => {
  React.useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [open])

  if (!open) return null

  return (
    <div 
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem'
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onOpenChange(false)
        }
      }}
    >
      {/* Backdrop */}
      <div 
        style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          backdropFilter: 'blur(4px)',
          zIndex: 9998
        }}
      />
      
      {/* Content */}
      <div style={{
        position: 'relative',
        zIndex: 9999,
        width: '100%',
        maxWidth: '32rem',
        margin: '0 auto'
      }}>
        {children}
      </div>
    </div>
  )
}

const DialogContent = React.forwardRef<HTMLDivElement, DialogContentProps>(
  ({ className, children, ...props }, ref) => {
    const isDark = document.documentElement.classList.contains('dark')
    return (
      <div
        ref={ref}
        style={{
          position: 'relative',
          backgroundColor: isDark ? '#1f2937' : '#ffffff',
          borderRadius: '0.5rem',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
          border: `1px solid ${isDark ? '#374151' : '#e5e7eb'}`,
          padding: '1.5rem',
          maxHeight: '90vh',
          overflowY: 'auto',
          width: '100%'
        }}
        className={cn(className)}
        {...props}
      >
        {children}
      </div>
    )
  }
)
DialogContent.displayName = "DialogContent"

const DialogHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn("flex flex-col space-y-1.5 mb-4", className)}
    {...props}
  />
)

const DialogTitle = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-lg font-semibold leading-none tracking-tight", className)}
    {...props}
  />
))
DialogTitle.displayName = "DialogTitle"

const DialogDescription = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-sm text-gray-500 dark:text-gray-400", className)}
    {...props}
  />
))
DialogDescription.displayName = "DialogDescription"

const DialogFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 mt-4", className)}
    {...props}
  />
)

const DialogClose = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & {
    onClose: () => void | Promise<void>
  }
>(({ className, onClose, disabled, ...props }, ref) => {
  const [isClosing, setIsClosing] = React.useState(false)
  const isDark = document.documentElement.classList.contains('dark')
  
  const handleClick = async (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault()
    e.stopPropagation()
    if (disabled || isClosing) return
    
    setIsClosing(true)
    try {
      await onClose()
    } catch (error) {
      console.error('Error closing dialog:', error)
      setIsClosing(false)
    }
  }
  
  return (
    <button
      ref={ref}
      type="button"
      onClick={handleClick}
      disabled={disabled || isClosing}
      style={{
        position: 'absolute',
        right: '1rem',
        top: '1rem',
        borderRadius: '0.125rem',
        opacity: (disabled || isClosing) ? 0.5 : 0.7,
        transition: 'opacity 0.2s',
        backgroundColor: 'transparent',
        border: 'none',
        cursor: (disabled || isClosing) ? 'not-allowed' : 'pointer',
        padding: '0.25rem',
        color: isDark ? '#9ca3af' : '#6b7280',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}
      onMouseEnter={(e) => {
        if (!disabled && !isClosing) {
          e.currentTarget.style.opacity = '1'
          e.currentTarget.style.color = isDark ? '#f9fafb' : '#111827'
        }
      }}
      onMouseLeave={(e) => {
        if (!disabled && !isClosing) {
          e.currentTarget.style.opacity = '0.7'
          e.currentTarget.style.color = isDark ? '#9ca3af' : '#6b7280'
        }
      }}
      className={cn(className)}
      {...props}
    >
      <X size={16} />
      <span style={{ position: 'absolute', width: '1px', height: '1px', padding: 0, margin: '-1px', overflow: 'hidden', clip: 'rect(0, 0, 0, 0)', whiteSpace: 'nowrap', borderWidth: 0 }}>关闭</span>
    </button>
  )
})
DialogClose.displayName = "DialogClose"

export { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose }
