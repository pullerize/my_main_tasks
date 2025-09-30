import React, { createContext, useContext, useState, useEffect } from 'react'

interface SidebarContextType {
  isCollapsed: boolean
  toggleSidebar: () => void
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined)

export const SidebarProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [isManualToggle, setIsManualToggle] = useState(false)

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth
      console.log('Screen width:', width, 'isManualToggle:', isManualToggle)

      if (width <= 1500 && !isManualToggle) {
        console.log('Auto-collapsing sidebar')
        setIsCollapsed(true)
      } else if (width > 1500 && !isManualToggle) {
        console.log('Auto-expanding sidebar')
        setIsCollapsed(false)
      }
    }

    // Set initial state
    handleResize()

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [isManualToggle])

  // Reset manual toggle on initial load to ensure auto-collapse works
  useEffect(() => {
    setIsManualToggle(false)
  }, [])

  const toggleSidebar = () => {
    setIsCollapsed(!isCollapsed)
    setIsManualToggle(true)

    // Reset manual toggle after some time to allow auto-collapse to work again
    setTimeout(() => {
      setIsManualToggle(false)
    }, 5000)
  }

  return (
    <SidebarContext.Provider value={{ isCollapsed, toggleSidebar }}>
      {children}
    </SidebarContext.Provider>
  )
}

export const useSidebar = () => {
  const context = useContext(SidebarContext)
  if (context === undefined) {
    throw new Error('useSidebar must be used within a SidebarProvider')
  }
  return context
}