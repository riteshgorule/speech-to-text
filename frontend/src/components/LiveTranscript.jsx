import { useState } from 'react'

export default function LiveTranscript() {
  const [message, setMessage] = useState('')
  const [running, setRunning] = useState(false)

  async function startLive() {
    setRunning(true)
    setMessage('Starting live transcription...')
    try {
      const res = await fetch('/api/live-transcribe')
      const data = await res.json()
      setMessage(data.status || JSON.stringify(data))
    } catch (e) {
      setMessage('Error: ' + e.message)
    } finally {
      setRunning(false)
    }
  }

  async function stopLive() {
    setRunning(false)
    setMessage('Stopping...')
    try {
      const res = await fetch('/api/live-stop', { method: 'POST' })
      const data = await res.json()
      setMessage(data.status || JSON.stringify(data))
    } catch (e) {
      setMessage('Error: ' + e.message)
    }
  }

  return (
    <div>
      <h2>Live Transcript</h2>
      <p>This will trigger the backend to start streaming from your microphone (server-side - check backend console where the server runs).</p>
      <div style={{display:'flex',gap:8}}>
        <button onClick={startLive} disabled={running}>
          {running ? 'Starting...' : 'Start Live Transcription'}
        </button>
        <button onClick={stopLive} disabled={!running}>
          Stop
        </button>
      </div>
      <div style={{marginTop:12}}>
        <strong>Server message:</strong>
        <div>{message}</div>
      </div>
    </div>
  )
}
