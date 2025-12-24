import type { AppProps } from 'next/app'
import { AuthProvider } from '../contexts/AuthContext'
import { Header } from '../components/Header'
import '../lib/amplify'
import '../styles/globals.css'

export default function App({ Component, pageProps }: AppProps) {
  return (
    <AuthProvider>
      <Header />
      <Component {...pageProps} />
    </AuthProvider>
  )
}

