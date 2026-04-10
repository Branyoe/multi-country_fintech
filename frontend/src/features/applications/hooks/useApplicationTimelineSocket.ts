import { useEffect, useRef, useState } from 'react'

import { useAuthStore } from '~/features/auth/store'
import { tokenStorage } from '~/lib/auth'
import type { TimelineTransitionEvent } from '~/features/applications/types'

type SocketStatus = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'disconnected'

interface UseApplicationTimelineSocketParams {
  applicationId?: string
  onTransition: (event: TimelineTransitionEvent) => void
}

const reconnectDelays = [1000, 2000, 4000, 8000, 10000]

function getWebSocketBaseUrl() {
  const configuredBase = import.meta.env.VITE_WS_BASE_URL as string | undefined
  if (configuredBase) {
    return configuredBase.replace(/\/$/, '')
  }

  const apiBase = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'
  if (apiBase.startsWith('http://') || apiBase.startsWith('https://')) {
    const parsed = new URL(apiBase)
    const protocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${parsed.host}`
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}`
}

export function useApplicationTimelineSocket({
  applicationId,
  onTransition,
}: UseApplicationTimelineSocketParams) {
  const token = useAuthStore((state) => state.accessToken)
  const [status, setStatus] = useState<SocketStatus>('idle')
  const socketRef = useRef<WebSocket | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimerRef = useRef<number | null>(null)
  const hasConnectedRef = useRef(false)
  const refreshAttemptedRef = useRef(false)
  const refreshInFlightRef = useRef(false)

  useEffect(() => {
    if (!applicationId || !token) {
      setStatus('idle')
      return
    }

    let stopped = false

    const cleanupTimer = () => {
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = null
      }
    }

    const connect = () => {
      if (stopped) return

      setStatus(reconnectAttemptsRef.current > 0 ? 'reconnecting' : 'connecting')
      hasConnectedRef.current = false

      const baseUrl = getWebSocketBaseUrl()
      const wsUrl = `${baseUrl}/ws/applications/${applicationId}/timeline/?token=${encodeURIComponent(token)}`
      const socket = new WebSocket(wsUrl)
      socketRef.current = socket

      socket.onopen = () => {
        reconnectAttemptsRef.current = 0
        hasConnectedRef.current = true
        refreshAttemptedRef.current = false
        setStatus('connected')
      }

      socket.onmessage = (messageEvent) => {
        try {
          const payload = JSON.parse(String(messageEvent.data)) as TimelineTransitionEvent
          if (payload.event === 'timeline.transition.created') {
            onTransition(payload)
          }
        } catch {
          // Ignore malformed socket payloads without crashing timeline rendering.
        }
      }

      socket.onclose = () => {
        if (stopped) {
          setStatus('disconnected')
          return
        }

        if (!hasConnectedRef.current) {
          const refresh = tokenStorage.getRefresh()
          if (refresh && !refreshAttemptedRef.current && !refreshInFlightRef.current) {
            refreshAttemptedRef.current = true
            refreshInFlightRef.current = true
            setStatus('reconnecting')

            void (async () => {
              try {
                const apiBase = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'
                const response = await fetch(`${apiBase}/auth/token/refresh/`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ refresh }),
                })
                if (!response.ok) return
                const data = (await response.json()) as { access?: string }
                if (data.access) {
                  useAuthStore.getState().setTokens(data.access, refresh)
                }
              } finally {
                refreshInFlightRef.current = false
              }
            })()

            return
          }
        }

        const attempt = reconnectAttemptsRef.current
        const delay = reconnectDelays[Math.min(attempt, reconnectDelays.length - 1)]
        reconnectAttemptsRef.current += 1
        setStatus('reconnecting')
        reconnectTimerRef.current = window.setTimeout(connect, delay)
      }

      socket.onerror = () => {
        socket.close()
      }
    }

    connect()

    return () => {
      stopped = true
      cleanupTimer()
      socketRef.current?.close()
      socketRef.current = null
      setStatus('disconnected')
    }
  }, [applicationId, onTransition, token])

  return { status }
}
