'use client'

import Link from 'next/link'

export default function CopyGeneratePage() {
  return (
    <div className="homepage-container">
      <div className="homepage-header">
        <div className="header-top" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', padding: '0 20px' }}>
          <div className="logo-container" style={{ display: 'flex', justifyContent: 'flex-start', flex: '1' }}>
            <img
              src="https://cf.quizizz.com/practice/branding/VoyageMathPremium.png"
              alt="VM Logo"
              className="logo"
              onError={(e) => {
                const target = e.target as HTMLImageElement
                target.src = '/static/images/logo.png'
                target.onerror = () => {
                  target.style.display = 'none'
                }
              }}
            />
          </div>
          <div className="wayground-container" style={{ display: 'flex', justifyContent: 'flex-end', flex: '1' }}>
            <img
              src="https://cdn.prod.website-files.com/68355113496452bf05789e95/68480ff9c322e13a2f937a22_Logo_Dark_Primary_Horizontal_MINIMUM.svg"
              alt="Wayground Logo"
              className="wayground-logo"
              onError={(e) => {
                const target = e.target as HTMLImageElement
                target.src = '/static/images/wayground-logo.svg'
                target.onerror = () => {
                  target.src = '/static/images/wayground-logo.png'
                  target.onerror = () => {
                    target.style.display = 'none'
                  }
                }
              }}
            />
          </div>
        </div>
        <h1>Copy Question Generator</h1>
        <p>Select the type of questions you want to generate</p>
      </div>

      <div className="homepage-buttons">
        <Link href="/generate?type=mathematical" className="homepage-btn mathematical">
          <span>Mathematical Questions</span>
          <hr style={{ border: 'none', borderTop: '2px solid white', margin: '15px 0', width: '100%' }} />
          <div className="image-previews" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', maxWidth: '120px', margin: '0 auto' }}>
            <div className="preview-item" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <svg width="50" height="50" viewBox="0 0 50 50" xmlns="http://www.w3.org/2000/svg">
                <line x1="25" y1="15" x2="25" y2="35" stroke="white" strokeWidth="3" strokeLinecap="round"/>
                <line x1="15" y1="25" x2="35" y2="25" stroke="white" strokeWidth="3" strokeLinecap="round"/>
              </svg>
            </div>
            <div className="preview-item" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <svg width="50" height="50" viewBox="0 0 50 50" xmlns="http://www.w3.org/2000/svg">
                <line x1="15" y1="25" x2="35" y2="25" stroke="white" strokeWidth="3" strokeLinecap="round"/>
              </svg>
            </div>
            <div className="preview-item" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <svg width="50" height="50" viewBox="0 0 50 50" xmlns="http://www.w3.org/2000/svg">
                <line x1="15" y1="15" x2="35" y2="35" stroke="white" strokeWidth="3" strokeLinecap="round"/>
                <line x1="35" y1="15" x2="15" y2="35" stroke="white" strokeWidth="3" strokeLinecap="round"/>
              </svg>
            </div>
            <div className="preview-item" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <svg width="50" height="50" viewBox="0 0 50 50" xmlns="http://www.w3.org/2000/svg">
                <circle cx="25" cy="15" r="2" fill="white"/>
                <line x1="15" y1="25" x2="35" y2="25" stroke="white" strokeWidth="2" strokeLinecap="round"/>
                <circle cx="25" cy="35" r="2" fill="white"/>
              </svg>
            </div>
          </div>
        </Link>
        <Link href="/generate?type=image-based" className="homepage-btn image-based">
          <span>Image based Questions</span>
          <hr style={{ border: 'none', borderTop: '2px solid white', margin: '15px 0', width: '100%' }} />
          <div className="image-previews" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', maxWidth: '120px', margin: '0 auto' }}>
            <div className="preview-item" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <svg width="50" height="50" viewBox="0 0 50 50" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="8" stroke="white" strokeWidth="1.5" fill="rgba(255,255,255,0.2)"/>
                <rect x="22" y="4" width="10" height="16" stroke="white" strokeWidth="1.5" fill="rgba(255,255,255,0.2)"/>
                <polygon points="38,4 45,20 31,20" stroke="white" strokeWidth="1.5" fill="rgba(255,255,255,0.2)"/>
                <rect x="8" y="24" width="10" height="10" stroke="white" strokeWidth="1.5" fill="rgba(255,255,255,0.2)"/>
                <polygon points="25,28 30,22 35,24 34,30 26,30" stroke="white" strokeWidth="1.5" fill="rgba(255,255,255,0.2)"/>
              </svg>
            </div>
            <div className="preview-item" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <svg width="50" height="50" viewBox="0 0 50 50" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <pattern id="grid" width="5" height="5" patternUnits="userSpaceOnUse">
                    <path d="M 5 0 L 0 0 0 5" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="0.5"/>
                  </pattern>
                </defs>
                <rect width="50" height="50" fill="url(#grid)"/>
                <line x1="5" y1="45" x2="45" y2="45" stroke="white" strokeWidth="2"/>
                <line x1="5" y1="45" x2="5" y2="5" stroke="white" strokeWidth="2"/>
                <line x1="5" y1="35" x2="45" y2="35" stroke="rgba(255,255,255,0.5)" strokeWidth="1"/>
                <line x1="5" y1="25" x2="45" y2="25" stroke="rgba(255,255,255,0.5)" strokeWidth="1"/>
                <line x1="5" y1="15" x2="45" y2="15" stroke="rgba(255,255,255,0.5)" strokeWidth="1"/>
                <line x1="15" y1="5" x2="15" y2="45" stroke="rgba(255,255,255,0.5)" strokeWidth="1"/>
                <line x1="25" y1="5" x2="25" y2="45" stroke="rgba(255,255,255,0.5)" strokeWidth="1"/>
                <line x1="35" y1="5" x2="35" y2="45" stroke="rgba(255,255,255,0.5)" strokeWidth="1"/>
                <polyline points="10,40 15,30 20,25 25,20 30,15 35,12 40,10" stroke="white" strokeWidth="2" fill="none"/>
              </svg>
            </div>
            <div className="preview-item" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <svg width="50" height="50" viewBox="0 0 50 50" xmlns="http://www.w3.org/2000/svg">
                <line x1="10" y1="25" x2="40" y2="25" stroke="white" strokeWidth="2"/>
                <line x1="10" y1="20" x2="10" y2="30" stroke="white" strokeWidth="2"/>
                <line x1="20" y1="20" x2="20" y2="30" stroke="white" strokeWidth="1.5"/>
                <line x1="30" y1="20" x2="30" y2="30" stroke="white" strokeWidth="1.5"/>
                <line x1="40" y1="20" x2="40" y2="30" stroke="white" strokeWidth="2"/>
                <text x="10" y="18" fill="white" fontSize="8" textAnchor="middle">0</text>
                <text x="20" y="18" fill="white" fontSize="8" textAnchor="middle">1</text>
                <text x="30" y="18" fill="white" fontSize="8" textAnchor="middle">2</text>
                <text x="40" y="18" fill="white" fontSize="8" textAnchor="middle">3</text>
              </svg>
            </div>
            <div className="preview-item" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <svg width="50" height="50" viewBox="0 0 50 50" xmlns="http://www.w3.org/2000/svg">
                <line x1="10" y1="40" x2="10" y2="10" stroke="white" strokeWidth="2"/>
                <line x1="10" y1="40" x2="40" y2="40" stroke="white" strokeWidth="2"/>
                <rect x="15" y="25" width="6" height="15" fill="white" opacity="0.8"/>
                <rect x="23" y="20" width="6" height="20" fill="white" opacity="0.8"/>
                <rect x="31" y="15" width="6" height="25" fill="white" opacity="0.8"/>
              </svg>
            </div>
            </div>
        </Link>
        <Link href="/generate?type=word-problems" className="homepage-btn word-problems">
          <span>Word Problems</span>
          <hr style={{ border: 'none', borderTop: '2px solid white', margin: '15px 0', width: '100%' }} />
          <div className="image-previews" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginTop: '10px' }}>
            <div className="preview-item" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <svg width="80" height="80" viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
                <rect x="15" y="10" width="50" height="60" rx="3" stroke="white" strokeWidth="2" fill="rgba(255,255,255,0.15)"/>
                <line x1="20" y1="20" x2="60" y2="20" stroke="white" strokeWidth="1.5"/>
                <line x1="20" y1="30" x2="55" y2="30" stroke="white" strokeWidth="1.5"/>
                <line x1="20" y1="40" x2="60" y2="40" stroke="white" strokeWidth="1.5"/>
                <line x1="20" y1="50" x2="50" y2="50" stroke="white" strokeWidth="1.5"/>
                <line x1="20" y1="60" x2="45" y2="60" stroke="white" strokeWidth="1.5"/>
                <line x1="35" y1="10" x2="35" y2="70" stroke="white" strokeWidth="1" strokeDasharray="2,2" opacity="0.5"/>
                <path d="M 50 15 L 50 25 L 45 20 Z" fill="white" opacity="0.8"/>
                <line x1="45" y1="20" x2="50" y2="20" stroke="white" strokeWidth="1.5"/>
                <line x1="48" y1="18" x2="48" y2="22" stroke="white" strokeWidth="1.5"/>
                <circle cx="52" cy="18" r="1.5" fill="white"/>
              </svg>
            </div>
          </div>
        </Link>
      </div>
    </div>
  )
}

