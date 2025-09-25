import { Link, Routes, Route, BrowserRouter } from 'react-router-dom'
import './App.css'
import Home from './components/Home'
import LiveTranscript from './components/LiveTranscript'
import PreRecorded from './components/PreRecorded'

function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <header>
          <h1>Speech Transcription</h1>
          <nav>
            <Link to="/">Home</Link>
            <Link to="/live">Live Transcript</Link>
            <Link to="/pre-recorded">Pre Recorded</Link>
          </nav>
        </header>

        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/live" element={<LiveTranscript />} />
            <Route path="/pre-recorded" element={<PreRecorded />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
