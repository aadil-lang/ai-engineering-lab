'use client'

import Link from 'next/link'

export default function Home() {
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
        <h1>Adaptive mathematics question generator</h1>
      </div>

      <div className="homepage-buttons" style={{ display: 'flex', gap: '40px', justifyContent: 'center', padding: '60px 40px', flexWrap: 'wrap' }}>
        <Link href="/base-generate" className="homepage-btn" style={{
          flex: '1',
          minWidth: '300px',
          maxWidth: '400px',
          padding: '40px',
          background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
          color: 'white',
          textDecoration: 'none',
          borderRadius: '20px',
          boxShadow: '0 10px 30px rgba(245, 87, 108, 0.4)',
          transition: 'all 0.3s ease',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          cursor: 'pointer'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'translateY(-5px)'
          e.currentTarget.style.boxShadow = '0 15px 40px rgba(245, 87, 108, 0.6)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'translateY(0)'
          e.currentTarget.style.boxShadow = '0 10px 30px rgba(245, 87, 108, 0.4)'
        }}>
          <h2 style={{ fontSize: '2em', marginBottom: '15px', fontWeight: '700' }}>Base Question Generator</h2>
          <p style={{ fontSize: '1.1em', opacity: 0.9, lineHeight: '1.6' }}>
            Generate base questions for your curriculum
          </p>
        </Link>

        <Link href="/copy-generate" className="homepage-btn" style={{
          flex: '1',
          minWidth: '300px',
          maxWidth: '400px',
          padding: '40px',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          textDecoration: 'none',
          borderRadius: '20px',
          boxShadow: '0 10px 30px rgba(102, 126, 234, 0.4)',
          transition: 'all 0.3s ease',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          cursor: 'pointer'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'translateY(-5px)'
          e.currentTarget.style.boxShadow = '0 15px 40px rgba(102, 126, 234, 0.6)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'translateY(0)'
          e.currentTarget.style.boxShadow = '0 10px 30px rgba(102, 126, 234, 0.4)'
        }}>
          <h2 style={{ fontSize: '2em', marginBottom: '15px', fontWeight: '700' }}>Copy Question Generator</h2>
          <p style={{ fontSize: '1.1em', opacity: 0.9, lineHeight: '1.6' }}>
            Generate multiple variations of questions based on a base question
          </p>
        </Link>
      </div>
    </div>
  )
}
