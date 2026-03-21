import React from 'react'
import ReactDOM from 'react-dom/client'
import App from '@/App.jsx'
import '@/globals.css'   // NeuroHire theme — must come before index.css
import '@/index.css'     // shadcn tokens — uses globals.css variables

ReactDOM.createRoot(document.getElementById('root')).render(
  <App />
)