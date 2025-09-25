import { useState } from 'react'

export default function PreRecorded() {
  const [url, setUrl] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  async function submitUrl(e) {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    try {
      const res = await fetch('/api/file-transcribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ audio_url: url })
      })
      const data = await res.json()
      setResult(data)
    } catch (err) {
      setResult({ error: err.message })
    } finally {
      setLoading(false)
    }
  }

  async function uploadFile(file) {
    setLoading(true)
    setResult(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/file-transcribe', {
        method: 'POST',
        body: form,
      })
      const data = await res.json()
      setResult(data)
    } catch (err) {
      setResult({ error: err.message })
    } finally {
      setLoading(false)
    }
  }

  function onFileChange(e) {
    const f = e.target.files && e.target.files[0]
    if (f) uploadFile(f)
  }

  function onDrop(e) {
    e.preventDefault()
    const f = e.dataTransfer.files && e.dataTransfer.files[0]
    if (f) uploadFile(f)
  }

  function onDragOver(e) {
    e.preventDefault()
  }

  return (
    <div>
      <h2>Pre-recorded Transcription</h2>
      <div>
        <form onSubmit={submitUrl} style={{marginBottom:12}}>
          <label>
            Audio URL:
            <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://.../audio.mp3" style={{width:'100%'}} />
          </label>
          <button type="submit" disabled={loading} style={{marginTop:8}}>
            {loading ? 'Transcribing...' : 'Transcribe URL'}
          </button>
        </form>

        <div onDrop={onDrop} onDragOver={onDragOver} style={{border:'2px dashed #ccc', padding:16, textAlign:'center'}}>
          <p>Or drag & drop an audio file here</p>
          <p>or</p>
          <input type="file" accept="audio/*" onChange={onFileChange} />
        </div>

        {result && (
          <div style={{marginTop:12}}>
            <h3>Result</h3>
            {result.transcript ? (
              <pre>{result.transcript}</pre>
            ) : (
              <pre>{JSON.stringify(result, null, 2)}</pre>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
