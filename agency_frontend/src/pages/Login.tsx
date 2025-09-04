import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_URL } from '../api'

function Login() {
  const [telegramUsername, setTelegramUsername] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    const savedLogin = localStorage.getItem('rememberLogin')
    const savedPass = localStorage.getItem('rememberPass')
    if (savedLogin && savedPass) {
      setTelegramUsername(savedLogin)
      setPassword(savedPass)
      setRemember(true)
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const res = await fetch(`${API_URL}/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          grant_type: 'password',
          username: telegramUsername,
          password,
        }),
      })
      if (res.ok) {
        const data = await res.json()
        
        if (remember) {
          localStorage.setItem('rememberLogin', telegramUsername)
          localStorage.setItem('rememberPass', password)
        } else {
          localStorage.removeItem('rememberLogin')
          localStorage.removeItem('rememberPass')
        }
        
        const me = await fetch(`${API_URL}/users/me`, {
          headers: { Authorization: `Bearer ${data.access_token}` },
        })
        if (me.ok) {
          const info = await me.json()
          console.log('DEBUG Login: User info from API:', info)
          console.log('DEBUG Login: Role from API:', info.role, typeof info.role)
          
          // Сохраняем всё одновременно чтобы избежать race condition
          localStorage.setItem('token', data.access_token)
          localStorage.setItem('role', info.role)
          localStorage.setItem('userId', String(info.id))
          
          console.log('DEBUG Login: Saved to localStorage:', {
            token: localStorage.getItem('token') ? 'exists' : 'missing',
            role: localStorage.getItem('role'),
            userId: localStorage.getItem('userId')
          })
          
          // Принудительно обновляем страницу чтобы App.tsx перечитал localStorage
          window.location.href = '/smm-projects'
        } else {
          console.error('DEBUG Login: Failed to get user info:', me.status, me.statusText)
          navigate('/smm-projects') // Fallback если не удалось получить информацию о пользователе
        }
      } else {
        setError('Invalid credentials')
      }
    } catch {
      setError('Unable to connect to server')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-gray-900 to-slate-900">
      <div className="max-w-md w-full space-y-8 p-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent mb-2">
            8BIT MEDIA
          </h1>
          <p className="text-gray-400 text-sm">Войдите в свой аккаунт</p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          <div className="bg-gray-800/50 backdrop-blur-lg rounded-2xl p-8 border border-gray-700/50 shadow-2xl">
            {error && (
              <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300 text-sm">
                {error}
              </div>
            )}
            
            <div className="space-y-4">
              <div>
                <label htmlFor="telegramUsername" className="block text-sm font-medium text-gray-300 mb-2">
                  Telegram Username
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400">@</span>
                  <input
                    id="telegramUsername"
                    type="text"
                    required
                    className="w-full pl-8 pr-4 py-3 bg-gray-700/50 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-300"
                    placeholder="pullerize"
                    value={telegramUsername}
                    onChange={(e) => setTelegramUsername(e.target.value.replace('@', ''))}
                  />
                </div>
                <p className="mt-1 text-xs text-gray-400">
                  Введите ваш Telegram username без символа @
                </p>
              </div>
              
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
                  Пароль
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  className="w-full px-4 py-3 bg-gray-700/50 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-300"
                  placeholder="Введите пароль"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            <div className="flex items-center mt-6">
              <input
                id="remember"
                type="checkbox"
                className="h-4 w-4 text-blue-500 focus:ring-blue-500 border-gray-600 bg-gray-700 rounded"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
              />
              <label htmlFor="remember" className="ml-2 block text-sm text-gray-300">
                Запомнить меня
              </label>
            </div>

            <button
              type="submit"
              className="w-full mt-6 bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 px-4 rounded-lg font-medium hover:from-blue-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-800 transform transition-all duration-300 hover:scale-105 shadow-lg"
            >
              Войти
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Login
