'use client'

import React, { useState, Suspense, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import DOMPurify from 'dompurify'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter } from 'recharts'

interface Question {
  question: string
  options: Array<{ text: string; logic: string }>
  image?: string
  solution?: string
  evalStatus?: {
    passed: boolean
    score: number
    issues: string[]
    calculatedAnswer?: string
  }
}

function GeneratePageContent() {
  const searchParams = useSearchParams()
  const questionType = searchParams.get('type')
  
  const [baseQuestion, setBaseQuestion] = useState('')
  const [numCopyQuestions, setNumCopyQuestions] = useState(5)
  const [notes, setNotes] = useState('')
  const [solution, setSolution] = useState('')
  const [images, setImages] = useState('')
  const [uploadedImages, setUploadedImages] = useState<File[]>([])
  const [imagePreviews, setImagePreviews] = useState<string[]>([])
  const [model, setModel] = useState('agnes-3-flash')
  const [loading, setLoading] = useState(false)
  const [loadingText, setLoadingText] = useState('')
  const [questions, setQuestions] = useState<Question[]>([])
  const [error, setError] = useState('')
  const [selectedQuestions, setSelectedQuestions] = useState<Set<number>>(new Set())
  const [verifyingQuestions, setVerifyingQuestions] = useState<Set<number>>(new Set())
  const [showSymbolToolbar, setShowSymbolToolbar] = useState(false)
  const [history, setHistory] = useState<string[]>([''])
  const [historyIndex, setHistoryIndex] = useState(0)
  const [copiedQuestionIndex, setCopiedQuestionIndex] = useState<number | null>(null)
  const [copiedSelected, setCopiedSelected] = useState(false)
  const [copiedAll, setCopiedAll] = useState(false)
  const [verificationMessage, setVerificationMessage] = useState<{index: number, message: string, type: 'success' | 'error'} | null>(null)
  const [showTableBuilder, setShowTableBuilder] = useState(false)
  const [tableData, setTableData] = useState<{rows: number, cols: number, data: string[][]}>({
    rows: 2,
    cols: 2,
    data: [['', ''], ['', '']]
  })
  const [hasHeader, setHasHeader] = useState(true)
  const [showChartBuilder, setShowChartBuilder] = useState(false)
  const [chartType, setChartType] = useState<'bar' | 'line' | 'dot' | 'scatter'>('bar')
  const [chartData, setChartData] = useState<Array<{name: string, value: number, label?: string}>>([
    { name: 'A', value: 10 },
    { name: 'B', value: 20 }
  ])
  const [chartTitle, setChartTitle] = useState('')
  const [xAxisLabel, setXAxisLabel] = useState('')
  const [yAxisLabel, setYAxisLabel] = useState('')
  const [yAxisMin, setYAxisMin] = useState<number | undefined>(undefined)
  const [yAxisMax, setYAxisMax] = useState<number | undefined>(undefined)
  const [showShapeBuilder, setShowShapeBuilder] = useState(false)
  const [shapeType, setShapeType] = useState<'triangle' | 'circle' | 'rectangle' | 'polygon'>('triangle')
  const [shapeData, setShapeData] = useState<any>({
    // Triangle
    sideA: 3,
    sideB: 4,
    sideC: 5,
    angleA: 90,
    angleB: 53.13,
    angleC: 36.87,
    type: 'right',
    // Circle
    radius: 5,
    diameter: 10,
    // Rectangle
    width: 6,
    height: 4,
    // Polygon
    sides: 5,
    sideLength: 3,
    isRegular: true
  })
  
  const pageTitle = questionType === 'mathematical' 
    ? 'Mathematical Questions Generator'
    : questionType === 'word-problems'
    ? 'Word Problems Generator'
    : questionType === 'image-based'
    ? 'Image-based Questions Generator'
    : 'Copy Question Generator'
  
  // Helper function to parse number of options from base question
  const parseNumberOfOptions = (question: string): number => {
    const foundOptions = new Set<string>()
    
    // Pattern 1: A), B), C), D) - letter followed by closing paren and space
    const pattern1 = /\b([A-Z])\)\s/gi
    const matches1 = Array.from(question.matchAll(pattern1))
    for (const match of matches1) {
      foundOptions.add(match[1].toUpperCase())
    }
    
    // Pattern 2: A. B. C. D. - letter followed by period and space
    const pattern2 = /\b([A-Z])\.\s/gi
    const matches2 = Array.from(question.matchAll(pattern2))
    for (const match of matches2) {
      foundOptions.add(match[1].toUpperCase())
    }
    
    // Pattern 3: (A), (B), (C), (D) - letter in parentheses
    const pattern3 = /\(([A-Z])\)/gi
    const matches3 = Array.from(question.matchAll(pattern3))
    for (const match of matches3) {
      foundOptions.add(match[1].toUpperCase())
    }
    
    // Pattern 4: Option A, Option B, Option C, Option D
    const pattern4 = /Option\s+([A-Z])[:\s]/gi
    const matches4 = Array.from(question.matchAll(pattern4))
    for (const match of matches4) {
      foundOptions.add(match[1].toUpperCase())
    }
    
    // Pattern 5: A) Text, B) Text (no space after paren)
    const pattern5 = /\b([A-Z])\)[^\s]/gi
    const matches5 = Array.from(question.matchAll(pattern5))
    for (const match of matches5) {
      foundOptions.add(match[1].toUpperCase())
    }
    
    // If we found letter options, determine the count
    if (foundOptions.size > 0) {
      const maxLetter = Array.from(foundOptions).sort().pop() || 'A'
      const numOptions = maxLetter.charCodeAt(0) - 'A'.charCodeAt(0) + 1
      if (numOptions >= 2 && numOptions <= 10) {
        return numOptions
      }
    }
    
    // Check for numbered options as fallback
    const numberedPatterns = [
      /\b(\d+)\)\s/g,  // 1), 2), 3), 4)
      /\b(\d+)\.\s/g,  // 1. 2. 3. 4.
    ]
    
    const numbers: number[] = []
    for (const pattern of numberedPatterns) {
      const matches = Array.from(question.matchAll(pattern))
      for (const match of matches) {
        const num = parseInt(match[1], 10)
        if (!isNaN(num)) {
          numbers.push(num)
        }
      }
    }
    
    if (numbers.length > 0) {
      const maxNum = Math.max(...numbers)
      if (maxNum >= 2 && maxNum <= 10) {
        return maxNum
      }
    }
    
    // Default to 4 if no options detected
    return 4
  }
  
  // Table Builder Functions
  const initializeTable = (rows: number, cols: number) => {
    const data: string[][] = []
    for (let i = 0; i < rows; i++) {
      data.push(Array(cols).fill(''))
    }
    return data
  }
  
  const addTableRow = () => {
    const newRows = tableData.rows + 1
    const newData = [...tableData.data, Array(tableData.cols).fill('')]
    setTableData({ ...tableData, rows: newRows, data: newData })
  }
  
  const removeTableRow = () => {
    if (tableData.rows > 1) {
      const newRows = tableData.rows - 1
      const newData = tableData.data.slice(0, -1)
      setTableData({ ...tableData, rows: newRows, data: newData })
    }
  }
  
  const addTableColumn = () => {
    const newCols = tableData.cols + 1
    const newData = tableData.data.map(row => [...row, ''])
    setTableData({ ...tableData, cols: newCols, data: newData })
  }
  
  const removeTableColumn = () => {
    if (tableData.cols > 1) {
      const newCols = tableData.cols - 1
      const newData = tableData.data.map(row => row.slice(0, -1))
      setTableData({ ...tableData, cols: newCols, data: newData })
    }
  }
  
  const updateTableCell = (rowIndex: number, colIndex: number, value: string) => {
    const newData = [...tableData.data]
    newData[rowIndex][colIndex] = value
    setTableData({ ...tableData, data: newData })
  }
  
  const convertTableToHTML = (): string => {
    let html = 'The image shows a data table:\n<table>\n'
    
    // Add header row if hasHeader is true
    if (hasHeader && tableData.data.length > 0) {
      html += '<tr>'
      tableData.data[0].forEach(cell => {
        html += `<th>${cell || 'Header'}</th>`
      })
      html += '</tr>\n'
      
      // Add data rows (skip first row if it's a header)
      for (let i = 1; i < tableData.data.length; i++) {
        html += '<tr>'
        tableData.data[i].forEach(cell => {
          html += `<td>${cell || ''}</td>`
        })
        html += '</tr>\n'
      }
    } else {
      // No header, all rows are data rows
      tableData.data.forEach(row => {
        html += '<tr>'
        row.forEach(cell => {
          html += `<td>${cell || ''}</td>`
        })
        html += '</tr>\n'
      })
    }
    
    html += '</table>'
    return html
  }
  
  const insertTableIntoImageDescription = () => {
    const tableHTML = convertTableToHTML()
    const currentValue = images.trim()
    const newValue = currentValue ? `${currentValue}\n\n${tableHTML}` : tableHTML
    setImages(newValue)
    setShowTableBuilder(false)
  }
  
  const resetTableBuilder = () => {
    setTableData({
      rows: 2,
      cols: 2,
      data: [['', ''], ['', '']]
    })
    setHasHeader(true)
  }
  
  // Chart Builder Functions
  const addChartDataPoint = () => {
    setChartData([...chartData, { name: `Item ${chartData.length + 1}`, value: 0 }])
  }
  
  const removeChartDataPoint = (index: number) => {
    if (chartData.length > 1) {
      setChartData(chartData.filter((_, i) => i !== index))
    }
  }
  
  const updateChartDataPoint = (index: number, field: 'name' | 'value' | 'label', value: string | number) => {
    const newData = [...chartData]
    newData[index] = { ...newData[index], [field]: value }
    setChartData(newData)
  }
  
  const convertChartToHTML = (): string => {
    let html = ''
    
    if (chartType === 'bar' || chartType === 'line') {
      html = `The image shows a ${chartType === 'bar' ? 'bar chart' : 'line graph'}${chartTitle ? ` titled "${chartTitle}"` : ''}.\n`
      if (xAxisLabel || yAxisLabel) {
        html += `The ${xAxisLabel ? `x-axis is labeled "${xAxisLabel}"` : ''}${xAxisLabel && yAxisLabel ? ' and ' : ''}${yAxisLabel ? `y-axis is labeled "${yAxisLabel}"` : ''}.\n`
      }
      html += 'The data points are:\n<table>\n'
      html += '<tr><th>Category</th><th>Value</th></tr>\n'
      chartData.forEach(point => {
        html += `<tr><td>${point.name}</td><td>${point.value}</td></tr>\n`
      })
      html += '</table>'
    } else if (chartType === 'dot' || chartType === 'scatter') {
      html = `The image shows a ${chartType === 'dot' ? 'dot plot' : 'scatter plot'}${chartTitle ? ` titled "${chartTitle}"` : ''}.\n`
      if (chartType === 'dot') {
        html += `The dot plot shows the frequency of each value. Each dot represents one occurrence.\n`
      }
      if (xAxisLabel || (yAxisLabel && chartType !== 'dot')) {
        html += `The ${xAxisLabel ? `x-axis is labeled "${xAxisLabel}"` : ''}${xAxisLabel && yAxisLabel && chartType !== 'dot' ? ' and ' : ''}${yAxisLabel && chartType !== 'dot' ? `y-axis is labeled "${yAxisLabel}"` : ''}.\n`
      }
      html += 'The data points are:\n<table>\n'
      html += '<tr><th>x</th><th>y</th>'
      if (chartData.some(p => p.label)) {
        html += '<th>Label</th>'
      }
      html += '</tr>\n'
      chartData.forEach(point => {
        html += `<tr><td>${point.name}</td><td>${point.value}</td>`
        if (chartData.some(p => p.label)) {
          html += `<td>${point.label || ''}</td>`
        }
        html += '</tr>\n'
      })
      html += '</table>'
      if (chartType === 'dot') {
        const dotDescriptions = chartData.map(p => {
          const count = Math.round(p.value)
          return `${count} dot${count !== 1 ? 's' : ''} at x=${p.name}`
        }).join(', ')
        html += `\nNote: In the dot plot, there are ${dotDescriptions}.`
      }
    }
    
    return html
  }
  
  const insertChartIntoImageDescription = () => {
    const chartHTML = convertChartToHTML()
    const currentValue = images.trim()
    const newValue = currentValue ? `${currentValue}\n\n${chartHTML}` : chartHTML
    setImages(newValue)
    setShowChartBuilder(false)
  }
  
  const resetChartBuilder = () => {
    setChartType('bar')
    setChartData([
      { name: 'A', value: 10 },
      { name: 'B', value: 20 }
    ])
    setChartTitle('')
    setXAxisLabel('')
    setYAxisLabel('')
    setYAxisMin(undefined)
    setYAxisMax(undefined)
  }
  
  // Shape Builder Functions
  const updateShapeData = (field: string, value: number | string | boolean) => {
    setShapeData((prev: any) => ({ ...prev, [field]: value }))
  }
  
  // Validate triangle using triangle inequality theorem
  const validateTriangle = (): string | null => {
    if (shapeType !== 'triangle') return null
    
    const { sideA, sideB, sideC } = shapeData
    const a = sideA || 0
    const b = sideB || 0
    const c = sideC || 0
    
    if (a <= 0 || b <= 0 || c <= 0) {
      return 'All sides must be greater than 0'
    }
    
    // Triangle inequality: sum of any two sides must be greater than the third
    if (a + b <= c || a + c <= b || b + c <= a) {
      return 'Triangle inequality violated: sum of any two sides must be greater than the third'
    }
    
    return null
  }
  
  const convertShapeToHTML = (): string => {
    let html = ''
    
    if (shapeType === 'triangle') {
      const { sideA, sideB, sideC, angleA, angleB, angleC, type } = shapeData
      const triangleType = type || 'scalene'
      html = `The image shows a ${triangleType} triangle.\n`
      html += `The triangle has sides labeled: side A = ${sideA} cm, side B = ${sideB} cm, side C = ${sideC} cm.\n`
      if (angleA && angleB && angleC) {
        html += `The angles are: angle A = ${angleA}°, angle B = ${angleB}°, angle C = ${angleC}°.\n`
      }
      if (triangleType === 'right') {
        html += `The right angle is at the vertex where sides A and B meet.\n`
        html += `The triangle is positioned with side A as the base (horizontal) and side B as the height (vertical).\n`
      } else if (triangleType === 'equilateral') {
        html += `All three sides are equal in length.\n`
        html += `All three angles are 60°.\n`
      } else if (triangleType === 'isosceles') {
        html += `Two sides are equal in length.\n`
      }
    } else if (shapeType === 'circle') {
      const { radius, diameter } = shapeData
      html = `The image shows a circle.\n`
      if (radius) {
        html += `The circle has a radius of ${radius} cm.\n`
      }
      if (diameter) {
        html += `The circle has a diameter of ${diameter} cm.\n`
      }
      html += `The center of the circle is marked.\n`
    } else if (shapeType === 'rectangle') {
      const { width, height } = shapeData
      html = `The image shows a rectangle.\n`
      html += `The rectangle has a width of ${width} cm and a height of ${height} cm.\n`
      html += `The rectangle is positioned with the longer side horizontal.\n`
    } else if (shapeType === 'polygon') {
      const { sides, sideLength, isRegular } = shapeData
      const polygonName = sides === 3 ? 'triangle' : sides === 4 ? 'square' : sides === 5 ? 'pentagon' : sides === 6 ? 'hexagon' : `${sides}-sided polygon`
      html = `The image shows a ${isRegular ? 'regular' : ''} ${polygonName}.\n`
      html += `The ${polygonName} has ${sides} sides, each with length ${sideLength} cm.\n`
      if (isRegular) {
        html += `All sides are equal in length and all angles are equal.\n`
      }
    }
    
    return html
  }
  
  const insertShapeIntoImageDescription = () => {
    const shapeHTML = convertShapeToHTML()
    const currentValue = images.trim()
    const newValue = currentValue ? `${currentValue}\n\n${shapeHTML}` : shapeHTML
    setImages(newValue)
    setShowShapeBuilder(false)
  }
  
  const resetShapeBuilder = () => {
    setShapeType('triangle')
    setShapeData({
      sideA: 3,
      sideB: 4,
      sideC: 5,
      angleA: 90,
      angleB: 53.13,
      angleC: 36.87,
      type: 'right',
      radius: 5,
      diameter: 10,
      width: 6,
      height: 4,
      sides: 5,
      sideLength: 3,
      isRegular: true
    })
  }
  
  // Render shape as SVG
  const renderShapeSVG = () => {
    const svgSize = 300
    const centerX = svgSize / 2
    const centerY = svgSize / 2
    
    if (shapeType === 'triangle') {
      const { sideA, sideB, sideC, type, angleA } = shapeData
      let x1, y1, x2, y2, x3, y3
      
      // Calculate scale to fit triangle in viewport
      const maxSide = Math.max(sideA, sideB, sideC)
      const scale = (svgSize * 0.4) / maxSide
      
      if (type === 'right') {
        // Right triangle: place right angle at vertex A (bottom-left)
        // Use sideA as base, sideB as height (or vice versa if angleA is at different vertex)
        const base = sideA || 3
        const height = sideB || 4
        const baseScaled = base * scale
        const heightScaled = height * scale
        
        x1 = centerX - baseScaled / 2
        y1 = centerY + heightScaled / 2
        x2 = centerX + baseScaled / 2
        y2 = centerY + heightScaled / 2
        x3 = centerX - baseScaled / 2
        y3 = centerY - heightScaled / 2
      } else if (type === 'equilateral') {
        // Equilateral triangle: all sides equal
        const side = sideA || 5
        const sideScaled = side * scale
        const height = (Math.sqrt(3) / 2) * sideScaled
        
        x1 = centerX
        y1 = centerY - height / 2
        x2 = centerX - sideScaled / 2
        y2 = centerY + height / 2
        x3 = centerX + sideScaled / 2
        y3 = centerY + height / 2
      } else {
        // General triangle: use Law of Cosines to calculate angles, then position vertices
        const a = sideA || 3
        const b = sideB || 4
        const c = sideC || 5
        
        // Calculate angles using Law of Cosines
        const angleA_rad = Math.acos((b * b + c * c - a * a) / (2 * b * c))
        const angleB_rad = Math.acos((a * a + c * c - b * b) / (2 * a * c))
        
        // Position triangle: vertex A at origin, side AB along x-axis
        const aScaled = a * scale
        const bScaled = b * scale
        const cScaled = c * scale
        
        x1 = centerX - aScaled / 2
        y1 = centerY + (Math.sqrt(3) / 4) * aScaled
        x2 = centerX + aScaled / 2
        y2 = centerY + (Math.sqrt(3) / 4) * aScaled
        
        // Calculate third vertex using Law of Cosines
        const angleC_rad = Math.PI - angleA_rad - angleB_rad
        x3 = x1 + bScaled * Math.cos(angleC_rad)
        y3 = y1 - bScaled * Math.sin(angleC_rad)
      }
      
      return (
        <svg width={svgSize} height={svgSize} style={{ border: '1px solid #ddd', borderRadius: '4px' }}>
          <polygon
            points={`${x1},${y1} ${x2},${y2} ${x3},${y3}`}
            fill="none"
            stroke="#5a2d7a"
            strokeWidth="2"
          />
          {/* Side labels */}
          <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 + 15} textAnchor="middle" fontSize="11" fill="#5a2d7a">
            {sideC || 'C'} cm
          </text>
          <text x={(x1 + x3) / 2 - 10} y={(y1 + y3) / 2} textAnchor="middle" fontSize="11" fill="#5a2d7a">
            {sideB || 'B'} cm
          </text>
          <text x={(x2 + x3) / 2 + 10} y={(y2 + y3) / 2} textAnchor="middle" fontSize="11" fill="#5a2d7a">
            {sideA || 'A'} cm
          </text>
          {/* Vertex labels */}
          <circle cx={x1} cy={y1} r={4} fill="#5a2d7a" />
          <circle cx={x2} cy={y2} r={4} fill="#5a2d7a" />
          <circle cx={x3} cy={y3} r={4} fill="#5a2d7a" />
          <text x={x1} y={y1 - 8} textAnchor="middle" fontSize="12" fontWeight="bold" fill="#5a2d7a">
            A
          </text>
          <text x={x2} y={y2 - 8} textAnchor="middle" fontSize="12" fontWeight="bold" fill="#5a2d7a">
            B
          </text>
          <text x={x3} y={y3 - 8} textAnchor="middle" fontSize="12" fontWeight="bold" fill="#5a2d7a">
            C
          </text>
        </svg>
      )
    } else if (shapeType === 'circle') {
      const { radius } = shapeData
      const r = Math.min(radius * 10, svgSize * 0.3)
      
      return (
        <svg width={svgSize} height={svgSize} style={{ border: '1px solid #ddd', borderRadius: '4px' }}>
          <circle
            cx={centerX}
            cy={centerY}
            r={r}
            fill="none"
            stroke="#5a2d7a"
            strokeWidth="2"
          />
          <circle
            cx={centerX}
            cy={centerY}
            r={3}
            fill="#5a2d7a"
          />
          <line
            x1={centerX}
            y1={centerY}
            x2={centerX + r}
            y2={centerY}
            stroke="#5a2d7a"
            strokeWidth="1"
            strokeDasharray="5,5"
          />
          <text x={centerX + r / 2} y={centerY - 5} textAnchor="middle" fontSize="12" fill="#5a2d7a">
            r = {radius} cm
          </text>
        </svg>
      )
    } else if (shapeType === 'rectangle') {
      const { width, height } = shapeData
      const w = Math.min(width * 15, svgSize * 0.6)
      const h = Math.min(height * 15, svgSize * 0.6)
      
      return (
        <svg width={svgSize} height={svgSize} style={{ border: '1px solid #ddd', borderRadius: '4px' }}>
          <rect
            x={centerX - w / 2}
            y={centerY - h / 2}
            width={w}
            height={h}
            fill="none"
            stroke="#5a2d7a"
            strokeWidth="2"
          />
          <text x={centerX} y={centerY - h / 2 - 5} textAnchor="middle" fontSize="12" fill="#5a2d7a">
            {width} cm
          </text>
          <text x={centerX - w / 2 - 20} y={centerY} textAnchor="middle" fontSize="12" fill="#5a2d7a" transform={`rotate(-90 ${centerX - w / 2 - 20} ${centerY})`}>
            {height} cm
          </text>
        </svg>
      )
    } else if (shapeType === 'polygon') {
      const { sides, sideLength, isRegular } = shapeData
      const n = sides
      const r = Math.min(sideLength * 15, svgSize * 0.3)
      const points: string[] = []
      
      for (let i = 0; i < n; i++) {
        const angle = (2 * Math.PI * i) / n - Math.PI / 2
        const x = centerX + r * Math.cos(angle)
        const y = centerY + r * Math.sin(angle)
        points.push(`${x},${y}`)
      }
      
      return (
        <svg width={svgSize} height={svgSize} style={{ border: '1px solid #ddd', borderRadius: '4px' }}>
          <polygon
            points={points.join(' ')}
            fill="none"
            stroke="#5a2d7a"
            strokeWidth="2"
          />
          <text x={centerX} y={centerY + 5} textAnchor="middle" fontSize="12" fill="#5a2d7a">
            {sides} sides
          </text>
        </svg>
      )
    }
    
    return null
  }
  
  // Parse chart from image description
  const parseChartFromDescription = (imageDescription: string): {
    chartType: 'bar' | 'line' | 'dot' | 'scatter' | 'histogram' | null,
    chartData: Array<{name: string, value: number, label?: string}>,
    title: string,
    xAxisLabel: string,
    yAxisLabel: string
  } | null => {
    // Check if it's a chart description
    const lowerDesc = imageDescription.toLowerCase()
    const isBarChart = lowerDesc.includes('bar chart')
    const isLineGraph = lowerDesc.includes('line graph')
    const isDotPlot = lowerDesc.includes('dot plot')
    const isScatterPlot = lowerDesc.includes('scatter plot')
    const isHistogram = lowerDesc.includes('histogram')
    
    if (!isBarChart && !isLineGraph && !isDotPlot && !isScatterPlot && !isHistogram) {
      return null // Not a chart
    }
    
    const chartType = isBarChart ? 'bar' : isLineGraph ? 'line' : isDotPlot ? 'dot' : isScatterPlot ? 'scatter' : 'histogram'
    
    // Extract title
    const titleMatch = imageDescription.match(/titled\s+"([^"]+)"/i)
    const title = titleMatch ? titleMatch[1] : ''
    
    // Extract axis labels
    const xAxisMatch = imageDescription.match(/x-axis is labeled\s+"([^"]+)"/i)
    const xAxisLabel = xAxisMatch ? xAxisMatch[1] : ''
    
    const yAxisMatch = imageDescription.match(/y-axis is labeled\s+"([^"]+)"/i)
    const yAxisLabel = yAxisMatch ? yAxisMatch[1] : ''
    
    // Extract table data
    const tempDiv = document.createElement('div')
    tempDiv.innerHTML = imageDescription
    const table = tempDiv.querySelector('table')
    
    if (!table) return null
    
    const chartData: Array<{name: string, value: number, label?: string}> = []
    const rows = table.querySelectorAll('tr')
    
    rows.forEach((row, index) => {
      if (index === 0) return // Skip header row
      
      const cells = row.querySelectorAll('td')
      if (cells.length >= 2) {
        const name = cells[0].textContent?.trim() || ''
        const value = parseFloat(cells[1].textContent?.trim() || '0')
        const label = cells[2]?.textContent?.trim()
        
        chartData.push({
          name,
          value: isNaN(value) ? 0 : value,
          ...(label && { label })
        })
      }
    })
    
    return {
      chartType,
      chartData,
      title,
      xAxisLabel,
      yAxisLabel
    }
  }
  
  // Render chart component
  const renderChart = (chartInfo: {
    chartType: 'bar' | 'line' | 'dot' | 'scatter' | 'histogram',
    chartData: Array<{name: string, value: number, label?: string}>,
    title: string,
    xAxisLabel: string,
    yAxisLabel: string
  }) => {
    const { chartType, chartData, title, xAxisLabel, yAxisLabel } = chartInfo
    
    return (
      <div style={{ width: '100%', height: '300px', marginTop: '10px' }}>
        <ResponsiveContainer width="100%" height="100%">
          {chartType === 'bar' || chartType === 'histogram' ? (
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" label={xAxisLabel ? { value: xAxisLabel, position: 'insideBottom', offset: -5 } : undefined} />
              <YAxis label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft' } : undefined} />
              <Tooltip />
              <Legend />
              <Bar dataKey="value" fill="#5a2d7a" />
            </BarChart>
          ) : chartType === 'line' ? (
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" label={xAxisLabel ? { value: xAxisLabel, position: 'insideBottom', offset: -5 } : undefined} />
              <YAxis label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft' } : undefined} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="value" stroke="#5a2d7a" strokeWidth={2} />
            </LineChart>
          ) : chartType === 'dot' ? (
            <ScatterChart margin={{ top: 20, right: 20, bottom: 40, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                type="number"
                dataKey="x" 
                name={xAxisLabel || 'x'} 
                label={xAxisLabel ? { value: xAxisLabel, position: 'insideBottom', offset: -5 } : undefined}
                domain={[-0.5, chartData.length - 0.5]}
                ticks={chartData.map((_, i) => i)}
                tickFormatter={(value) => {
                  const index = Math.round(value)
                  const dataPoint = chartData[index]
                  return dataPoint ? dataPoint.name : ''
                }}
              />
              <YAxis 
                type="number"
                domain={[0, 'dataMax + 1']}
                hide={true}
              />
              <Tooltip 
                cursor={{ strokeDasharray: '3 3' }}
                formatter={(value: any, name: any, props: any) => {
                  return [`${props.payload.originalValue} dot${props.payload.originalValue !== 1 ? 's' : ''}`, 'Count']
                }}
              />
              <Scatter 
                data={chartData.flatMap((d, i) => {
                  const xValue = i
                  const yValue = Math.max(0, Math.round(d.value))
                  return Array.from({ length: yValue }, (_, dotIndex) => ({
                    x: xValue,
                    y: dotIndex + 1,
                    originalValue: yValue,
                    name: d.name
                  }))
                })} 
                fill="#5a2d7a"
                shape={(props: any) => {
                  const { cx, cy } = props
                  if (cx == null || cy == null || typeof cx !== 'number' || typeof cy !== 'number') {
                    return <g />
                  }
                  return (
                    <circle 
                      cx={cx} 
                      cy={cy} 
                      r={6} 
                      fill="#5a2d7a" 
                      stroke="#5a2d7a"
                      strokeWidth={1}
                    />
                  )
                }}
                dataKey="y"
              />
            </ScatterChart>
          ) : (
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" dataKey="x" name={xAxisLabel || 'x'} label={xAxisLabel ? { value: xAxisLabel, position: 'insideBottom', offset: -5 } : undefined} />
              <YAxis 
                type="number" 
                dataKey="y" 
                name={yAxisLabel || 'y'} 
                label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft' } : undefined}
              />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} />
              <Scatter data={chartData.map((d, i) => ({ x: parseFloat(d.name) || i, y: d.value }))} fill="#5a2d7a" />
            </ScatterChart>
          )}
        </ResponsiveContainer>
      </div>
    )
  }
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setQuestions([])
    
    const loadingMessages = [
      'Analyzing base question...',
      'Generating variations...',
      'Creating options...',
      'Validating questions...',
      'Almost done...'
    ]
    let messageIndex = 0
    const interval = setInterval(() => {
      setLoadingText(loadingMessages[messageIndex % loadingMessages.length])
      messageIndex++
    }, 2000)
    
    try {
      // Extract number of options from base question
      const numOptions = parseNumberOfOptions(baseQuestion)
      
      // Convert uploaded images to base64
      const imageBase64Array = uploadedImages.length > 0 
        ? await convertImagesToBase64(uploadedImages)
        : []
      
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          baseQuestion,
          numCopyQuestions,
          numOptions, // Explicitly send the number of options
          notes: notes.trim(), // Trim whitespace to ensure empty string if only whitespace
          solution,
          images,
          imageFiles: imageBase64Array,
          model,
          questionType: questionType || null,
        }),
      })
      
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to generate questions')
      }
      
      if (!data.questions || data.questions.length === 0) {
        throw new Error('No questions were generated. Please try again.')
      }
      
      setQuestions(data.questions)
      setSelectedQuestions(new Set())
    } catch (err: any) {
      setError(err.message || 'An error occurred')
    } finally {
      clearInterval(interval)
      setLoading(false)
      setLoadingText('')
    }
  }
  
  const copyQuestion = (index: number) => {
    const question = questions[index]
    const text = formatQuestionForCopy(question)
    navigator.clipboard.writeText(text)
    // Show green feedback
    setCopiedQuestionIndex(index)
    setTimeout(() => setCopiedQuestionIndex(null), 20000) // Reset after 20 seconds
  }
  
  const copySelected = () => {
    const selected = Array.from(selectedQuestions)
      .map(idx => formatQuestionForCopy(questions[idx]))
      .join('\n') // Single newline separates questions (each goes to one cell per row)
    navigator.clipboard.writeText(selected)
    // Show green feedback
    setCopiedSelected(true)
    setTimeout(() => setCopiedSelected(false), 20000) // Reset after 20 seconds
  }
  
  const copyAll = () => {
    // Join questions with newline so each question goes to a separate cell/row when pasted
    // Each question will be in its own cell with options wrapped to new lines within that cell
    const all = questions.map(q => formatQuestionForCopy(q)).join('\n')
    navigator.clipboard.writeText(all)
    // Show green feedback
    setCopiedAll(true)
    setTimeout(() => setCopiedAll(false), 20000) // Reset after 20 seconds
  }
  
  // Convert HTML table to TSV format for Google Docs compatibility
  const convertHTMLTableToTSV = (htmlString: string): string | null => {
    try {
      // Create a temporary DOM element to parse HTML
      const tempDiv = document.createElement('div')
      tempDiv.innerHTML = htmlString
      
      const table = tempDiv.querySelector('table')
      if (!table) return null // Return null if no table found
      
      const rows: string[] = []
      const tableRows = table.querySelectorAll('tr')
      
      tableRows.forEach((row) => {
        const cells: string[] = []
        const isHeaderRow = row.querySelector('th') !== null
        
        if (isHeaderRow) {
          row.querySelectorAll('th').forEach(cell => {
            const cellText = cell.textContent?.trim() || ''
            cells.push(cellText)
          })
        } else {
          row.querySelectorAll('td').forEach(cell => {
            const cellText = cell.textContent?.trim() || ''
            cells.push(cellText)
          })
        }
        
        if (cells.length > 0) {
          rows.push(cells.join('\t')) // Tab-separated values
        }
      })
      
      return rows.length > 0 ? rows.join('\n') : null // Newline-separated rows
    } catch (error) {
      console.error('Error converting HTML table to TSV:', error)
      return null
    }
  }
  
  const formatQuestionForCopy = (question: Question): string => {
    // Format: Question text with spacing, then each option on its own line (all in one cell)
    // Format: Question text followed by spaces so options wrap to next line
    // Each option also has spacing after it so the next option wraps to a new line
    // This ensures each option appears on its own line when pasted into spreadsheets with word wrap
    let text = question.question
    
    // Add image description below question text if it exists
    if (question.image) {
      // Check if image description contains an HTML table
      if (question.image.includes('<table>')) {
        // Convert HTML table to TSV format for Google Docs compatibility
        const tsvTable = convertHTMLTableToTSV(question.image)
        if (tsvTable) {
          text += '\n\nImage Description (Table):\n' + tsvTable
        } else {
          // Fallback: strip HTML tags if conversion fails
          const plainText = question.image.replace(/<[^>]*>/g, '').trim()
          text += '\n\nImage Description: ' + plainText
        }
      } else {
        // Regular image description (no table) - strip any HTML tags
        const plainText = question.image.replace(/<[^>]*>/g, '').trim()
        text += ' '.repeat(100) // Add spacing before image description
        text += `Image Description: ${plainText}`
      }
    }
    
    // Add multiple spaces to ensure first option wraps to next line
    text += ' '.repeat(100) // Add 100 spaces to push first option to next line
    
    // Add options with logic, each with spacing after to push next option to new line
    question.options.forEach((opt, idx) => {
      let optionText = `${String.fromCharCode(65 + idx)}) ${opt.text}`
      if (opt.logic === 'CA') {
        optionText += ' (Correct Answer)'
      } else if (opt.logic) {
        optionText += ` (Logic: ${opt.logic})`
      }
      text += optionText
      
      // Add spacing after each option (except the last one) to push next option to new line
      if (idx < question.options.length - 1) {
        text += ' '.repeat(100) // Add 100 spaces after each option
    }
    })
    
    return text
  }

  const verifyQuestion = async (index: number) => {
    const question = questions[index]
    if (!question) return

    // Prevent multiple simultaneous verifications
    if (verifyingQuestions.has(index)) return

    setVerifyingQuestions(prev => new Set(prev).add(index))
    setError('')
    setVerificationMessage(null) // Clear any previous message

    try {
      const response = await fetch('/api/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question.question,
          options: question.options,
          solution: question.solution || '',
          image: question.image || '',
          model: model,
          questionType: questionType || 'mathematical',
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to verify question')
      }

      if (data.verified && data.result) {
        const result = data.result
        
        // Update the question if corrections were made
        if (result.hasErrors) {
          // Check if corrections are actually different from original
          const correctedQuestion = result.correctedQuestion || question.question
          const correctedSolution = result.correctedSolution || question.solution
          let correctedOptions = result.correctedOptions || question.options
          
          // Ensure corrected options maintain the same count as original
          if (Array.isArray(correctedOptions) && correctedOptions.length !== question.options.length) {
            // If count doesn't match, adjust to maintain original count
            if (correctedOptions.length > question.options.length) {
              correctedOptions = correctedOptions.slice(0, question.options.length)
            } else if (correctedOptions.length < question.options.length) {
              // Pad with original options if needed
              const originalOptions = [...question.options]
              const newOptions = [...correctedOptions]
              while (newOptions.length < question.options.length) {
                const originalIndex = newOptions.length
                newOptions.push({
                  text: originalOptions[originalIndex].text,
                  logic: originalOptions[originalIndex].logic
                })
              }
              correctedOptions = newOptions
            }
          }
          
          // Check if options are actually different
          const optionsChanged = correctedOptions.some((opt: any, idx: number) => {
            const original = question.options[idx]
            return !original || opt.text !== original.text || opt.logic !== original.logic
          })
          
          const questionChanged = correctedQuestion !== question.question
          const solutionChanged = correctedSolution !== question.solution
          
          // Only update if something actually changed
          if (questionChanged || optionsChanged || solutionChanged) {
            setQuestions(prev => {
              const updated = [...prev]
              updated[index] = {
                question: correctedQuestion,
                options: correctedOptions,
                solution: correctedSolution,
                image: question.image,
              }
              return updated
            })
            
            // Show success message with verification notes (non-blocking)
            let message = `Question verified and corrected!\n\nErrors found:\n${result.errors?.join('\n') || 'N/A'}`
            
            // Add context correction information if context was corrected
            if (result.contextCorrected && result.contextIssues && result.contextIssues.length > 0) {
              message += `\n\n⚠️ Context Issues Found and Corrected:\n${result.contextIssues.join('\n')}\n\nThe question context has been updated to be more practical and reasonable while maintaining the same mathematical structure.`
            }
            
            message += `\n\n${result.verificationNotes || ''}`
            setVerificationMessage({ index, message, type: 'success' })
            setTimeout(() => setVerificationMessage(null), 12000) // Auto-dismiss after 12s (longer for context info)
          } else {
            // No actual changes, just show verification success
            setVerificationMessage({ index, message: 'Question verified successfully! No changes needed.', type: 'success' })
            setTimeout(() => setVerificationMessage(null), 5000) // Auto-dismiss after 5s
          }
        } else {
          setVerificationMessage({ index, message: 'Question verified successfully! No errors found.', type: 'success' })
          setTimeout(() => setVerificationMessage(null), 5000) // Auto-dismiss after 5s
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to verify question')
      setVerificationMessage({ index, message: err.message || 'Failed to verify question', type: 'error' })
      setTimeout(() => setError(''), 5000)
      setTimeout(() => setVerificationMessage(null), 5000)
    } finally {
      setVerifyingQuestions(prev => {
        const newSet = new Set(prev)
        newSet.delete(index)
        return newSet
      })
    }
  }

  const saveToHistory = (value: string) => {
    const newHistory = history.slice(0, historyIndex + 1)
    newHistory.push(value)
    setHistory(newHistory)
    setHistoryIndex(newHistory.length - 1)
  }

  const undo = () => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1
      setHistoryIndex(newIndex)
      setBaseQuestion(history[newIndex])
    }
  }

  const redo = () => {
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1
      setHistoryIndex(newIndex)
      setBaseQuestion(history[newIndex])
    }
  }

  const insertAtCursor = (text: string) => {
    const textarea = document.getElementById('baseQuestion') as HTMLTextAreaElement
    if (!textarea) return

    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const currentValue = baseQuestion
    const newValue = currentValue.substring(0, start) + text + currentValue.substring(end)
    
    setBaseQuestion(newValue)
    saveToHistory(newValue)
    
    // Set cursor position after inserted text
    setTimeout(() => {
      textarea.focus()
      const newCursorPos = start + text.length
      textarea.setSelectionRange(newCursorPos, newCursorPos)
    }, 0)
  }

  const handleBaseQuestionChange = (value: string) => {
    setBaseQuestion(value)
    saveToHistory(value)
  }

  const insertSymbol = (symbol: string) => {
    insertAtCursor(symbol)
  }

  const mathSymbols = [
    { label: '+', value: '+' },
    { label: '−', value: '−' },
    { label: '×', value: '×' },
    { label: '÷', value: '÷' },
    { label: '=', value: '=' },
    { label: '≠', value: '≠' },
    { label: '<', value: '<' },
    { label: '>', value: '>' },
    { label: '≤', value: '≤' },
    { label: '≥', value: '≥' },
    { label: '±', value: '±' },
    { label: '√', value: '√' },
    { label: '∛', value: '∛' },
    { label: 'π', value: 'π' },
    { label: '°', value: '°' },
    { label: '²', value: '²' },
    { label: '³', value: '³' },
    { label: '∞', value: '∞' },
    { label: '∑', value: '∑' },
    { label: '∫', value: '∫' },
    { label: '≈', value: '≈' },
    { label: '∠', value: '∠' },
    { label: '(', value: '(' },
    { label: ')', value: ')' },
    { label: '[', value: '[' },
    { label: ']', value: ']' },
    { label: '{', value: '{' },
    { label: '}', value: '}' },
    { label: '∇', value: '∇' }, // gradient
    { label: 'Δ', value: 'Δ' }, // delta
    { label: '≅', value: '≅' }, // approxequalto (congruent to)
    { label: '≡', value: '≡' }, // identicalto
    { label: '/', value: '/' }, // slash
    { label: '\\', value: '\\' }, // backslash
    { label: '△', value: '△' }, // triangle
    { label: '·', value: '·' } // dot
  ]
  
  const toggleSelection = (index: number) => {
    const newSelected = new Set(selectedQuestions)
    if (newSelected.has(index)) {
      newSelected.delete(index)
    } else {
      newSelected.add(index)
    }
    setSelectedQuestions(newSelected)
  }
  
  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return
    
    const newFiles = Array.from(files)
    const validFiles = newFiles.filter(file => {
      const isValidType = file.type.startsWith('image/')
      const isValidSize = file.size <= 10 * 1024 * 1024 // 10MB limit
      return isValidType && isValidSize
    })
    
    if (validFiles.length !== newFiles.length) {
      setError('Some files were rejected. Only image files under 10MB are allowed.')
      setTimeout(() => setError(''), 5000)
    }
    
    setUploadedImages(prev => [...prev, ...validFiles])
    
    // Create previews
    validFiles.forEach(file => {
      const reader = new FileReader()
      reader.onloadend = () => {
        setImagePreviews(prev => [...prev, reader.result as string])
      }
      reader.readAsDataURL(file)
    })
  }
  
  const removeImage = (index: number) => {
    setUploadedImages(prev => prev.filter((_, i) => i !== index))
    setImagePreviews(prev => prev.filter((_, i) => i !== index))
  }
  
  const convertImagesToBase64 = async (files: File[]): Promise<string[]> => {
    const base64Promises = files.map(file => {
      return new Promise<string>((resolve, reject) => {
        const reader = new FileReader()
        reader.onloadend = () => {
          const base64String = reader.result as string
          resolve(base64String)
        }
        reader.onerror = reject
        reader.readAsDataURL(file)
      })
    })
    return Promise.all(base64Promises)
  }
  
  return (
    <div className="container">
      <header style={{ padding: '40px 30px', minHeight: '180px', position: 'relative' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', marginTop: '10px' }}>
          <div className="logo-container" style={{ flex: '1', display: 'flex', justifyContent: 'flex-start' }}>
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
          <div className="wayground-container" style={{ flex: '1', display: 'flex', justifyContent: 'flex-end' }}>
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
        <h1 style={{ textAlign: 'center', marginTop: '20px' }}>{pageTitle}</h1>
      </header>
      
      <main>
        <form onSubmit={handleSubmit} className="form-container">
          <div className="form-group">
            <label htmlFor="baseQuestion">Enter Base Question *</label>
            
            {/* Unified Toolbar */}
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
              marginBottom: '8px',
              padding: '8px',
              backgroundColor: '#f8f9fa',
              borderRadius: '6px',
              border: '1px solid #e0e0e0'
            }}>
              {/* Toolbar Controls Row */}
              <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '6px',
                alignItems: 'center',
                marginBottom: showSymbolToolbar ? '6px' : '0',
                paddingBottom: showSymbolToolbar ? '6px' : '0',
                borderBottom: showSymbolToolbar ? '1px solid #e0e0e0' : 'none'
              }}>
                {/* Undo Button */}
                <button
                  type="button"
                  onClick={undo}
                  disabled={historyIndex <= 0}
                  style={{
                    padding: '4px 10px',
                    fontSize: '12px',
                    fontWeight: '600',
                    backgroundColor: historyIndex > 0 ? '#fff' : '#f0f0f0',
                    color: historyIndex > 0 ? '#5a2d7a' : '#999',
                    border: '1px solid #ccc',
                    borderRadius: '3px',
                    cursor: historyIndex > 0 ? 'pointer' : 'not-allowed',
                    transition: 'all 0.2s',
                    height: '28px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    whiteSpace: 'nowrap'
                  }}
                  onMouseEnter={(e) => {
                    if (historyIndex > 0) {
                      e.currentTarget.style.backgroundColor = '#e6d5f7'
                      e.currentTarget.style.borderColor = '#5a2d7a'
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (historyIndex > 0) {
                      e.currentTarget.style.backgroundColor = '#fff'
                      e.currentTarget.style.borderColor = '#ccc'
                    }
                  }}
                  title="Undo"
                >
                  ↶ Undo
                </button>
                
                {/* Redo Button */}
                <button
                  type="button"
                  onClick={redo}
                  disabled={historyIndex >= history.length - 1}
                  style={{
                    padding: '4px 10px',
                    fontSize: '12px',
                    fontWeight: '600',
                    backgroundColor: historyIndex < history.length - 1 ? '#fff' : '#f0f0f0',
                    color: historyIndex < history.length - 1 ? '#5a2d7a' : '#999',
                    border: '1px solid #ccc',
                    borderRadius: '3px',
                    cursor: historyIndex < history.length - 1 ? 'pointer' : 'not-allowed',
                    transition: 'all 0.2s',
                    height: '28px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    whiteSpace: 'nowrap'
                  }}
                  onMouseEnter={(e) => {
                    if (historyIndex < history.length - 1) {
                      e.currentTarget.style.backgroundColor = '#e6d5f7'
                      e.currentTarget.style.borderColor = '#5a2d7a'
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (historyIndex < history.length - 1) {
                      e.currentTarget.style.backgroundColor = '#fff'
                      e.currentTarget.style.borderColor = '#ccc'
                    }
                  }}
                  title="Redo"
                >
                  ↷ Redo
                </button>
                
                {/* Symbols Toggle */}
                <button
                  type="button"
                  onClick={() => setShowSymbolToolbar(!showSymbolToolbar)}
                  style={{
                    padding: '4px 10px',
                    fontSize: '12px',
                    fontWeight: '600',
                    backgroundColor: showSymbolToolbar ? '#5a2d7a' : '#fff',
                    color: showSymbolToolbar ? '#fff' : '#5a2d7a',
                    border: '1px solid #5a2d7a',
                    borderRadius: '3px',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    height: '28px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    whiteSpace: 'nowrap'
                  }}
                  onMouseEnter={(e) => {
                    if (!showSymbolToolbar) {
                      e.currentTarget.style.backgroundColor = '#e6d5f7'
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!showSymbolToolbar) {
                      e.currentTarget.style.backgroundColor = '#fff'
                    }
                  }}
                  title={showSymbolToolbar ? 'Hide symbols' : 'Show symbols'}
                >
                  {showSymbolToolbar ? '▼ Symbols' : '▶ Symbols'}
                </button>
              </div>
              
              {/* Mathematical Symbol Toolbar */}
              {showSymbolToolbar && (
                <div style={{ 
                  display: 'flex', 
                  flexWrap: 'wrap', 
                  gap: '4px',
                  alignItems: 'center'
                }}>
                  {mathSymbols.map((symbol, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => insertSymbol(symbol.value)}
                      style={{
                        padding: '4px 8px',
                        fontSize: '14px',
                        fontWeight: 'bold',
                        backgroundColor: '#fff',
                        border: '1px solid #ccc',
                        borderRadius: '3px',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        minWidth: '28px',
                        height: '28px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = '#e6d5f7'
                        e.currentTarget.style.borderColor = '#5a2d7a'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = '#fff'
                        e.currentTarget.style.borderColor = '#ccc'
                      }}
                      title={`Insert ${symbol.label}`}
                    >
                      {symbol.label}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <textarea
              id="baseQuestion"
              value={baseQuestion}
              onChange={(e) => handleBaseQuestionChange(e.target.value)}
              rows={4}
              required
              placeholder="Enter your base question here... Use the toolbar above to insert mathematical symbols."
            />
          </div>
          
          {questionType === 'image-based' && (
            <>
            <div className="form-group">
                <label htmlFor="images">Image Description (if any)</label>
              <div style={{
                border: '2px solid #e0e0e0',
                borderRadius: '8px',
                padding: '12px',
                backgroundColor: '#fff',
                transition: 'border-color 0.3s'
              }}>
                {/* Toolbar for Image Description */}
                <div style={{
                  display: 'flex',
                  gap: '8px',
                  marginBottom: '10px',
                  paddingBottom: '10px',
                  borderBottom: '1px solid #e0e0e0',
                  flexWrap: 'wrap',
                  alignItems: 'center'
                }}>
                  <button
                    type="button"
                    onClick={() => setShowTableBuilder(true)}
                    style={{
                      padding: '4px 10px',
                      fontSize: '12px',
                      fontWeight: '600',
                      backgroundColor: '#fff',
                      color: '#5a2d7a',
                      border: '1px solid #5a2d7a',
                      borderRadius: '3px',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      height: '28px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      whiteSpace: 'nowrap'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = '#e6d5f7'
                      e.currentTarget.style.borderColor = '#5a2d7a'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = '#fff'
                      e.currentTarget.style.borderColor = '#5a2d7a'
                    }}
                    title="Build HTML Table"
                  >
                    📊 Build Table
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowChartBuilder(true)}
                    style={{
                      padding: '4px 10px',
                      fontSize: '12px',
                      fontWeight: '600',
                      backgroundColor: '#fff',
                      color: '#5a2d7a',
                      border: '1px solid #5a2d7a',
                      borderRadius: '3px',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      height: '28px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      whiteSpace: 'nowrap'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = '#e6d5f7'
                      e.currentTarget.style.borderColor = '#5a2d7a'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = '#fff'
                      e.currentTarget.style.borderColor = '#5a2d7a'
                    }}
                    title="Build Chart"
                  >
                    📈 Build Chart
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowShapeBuilder(true)}
                    style={{
                      padding: '4px 10px',
                      fontSize: '12px',
                      fontWeight: '600',
                      backgroundColor: '#fff',
                      color: '#5a2d7a',
                      border: '1px solid #5a2d7a',
                      borderRadius: '3px',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      height: '28px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      whiteSpace: 'nowrap'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = '#e6d5f7'
                      e.currentTarget.style.borderColor = '#5a2d7a'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = '#fff'
                      e.currentTarget.style.borderColor = '#5a2d7a'
                    }}
                    title="Build Geometric Shape"
                  >
                    🔷 Build Shape
                  </button>
                </div>
                
                <textarea
                  id="images"
                  value={images}
                  onChange={(e) => setImages(e.target.value)}
                  placeholder="Enter image description or URLs (comma-separated). Use the Table Builder or Chart Builder buttons above to create HTML tables or chart descriptions."
                  rows={4}
                  style={{
                    width: '100%',
                    border: 'none',
                    outline: 'none',
                    resize: 'vertical',
                    fontFamily: 'monospace',
                    fontSize: '13px',
                    padding: '0',
                    backgroundColor: 'transparent'
                  }}
                />
              </div>
            </div>
          
          <div className="form-group">
                <label htmlFor="imageUpload">Upload Images</label>
            <input
                  type="file"
                  id="imageUpload"
                  accept="image/*"
                  multiple
                  onChange={handleImageUpload}
                  style={{ display: 'none' }}
                />
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    onClick={() => document.getElementById('imageUpload')?.click()}
                    className="btn btn-secondary"
                    style={{ marginBottom: '10px' }}
                  >
                    📷 Upload Images
                  </button>
                  {uploadedImages.length > 0 && (
                    <span style={{ color: '#666', fontSize: '14px' }}>
                      {uploadedImages.length} image{uploadedImages.length > 1 ? 's' : ''} selected
                    </span>
                  )}
                </div>
                
                {imagePreviews.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: '10px' }}>
                    {imagePreviews.map((preview, index) => (
                      <div key={index} style={{ position: 'relative', display: 'inline-block' }}>
                        <img
                          src={preview}
                          alt={`Preview ${index + 1}`}
                          style={{
                            width: '100px',
                            height: '100px',
                            objectFit: 'cover',
                            border: '1px solid #ddd',
                            borderRadius: '4px',
                            cursor: 'pointer'
                          }}
                        />
                        <button
                          type="button"
                          onClick={() => removeImage(index)}
                          style={{
                            position: 'absolute',
                            top: '-8px',
                            right: '-8px',
                            background: '#ff4444',
                            color: 'white',
                            border: 'none',
                            borderRadius: '50%',
                            width: '24px',
                            height: '24px',
                            cursor: 'pointer',
                            fontSize: '14px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                          }}
                          title="Remove image"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                )}
          </div>
            </>
          )}
          
          <div className="form-group">
            <label htmlFor="notes">SME Notes</label>
            <textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Enter any notes related to the base question..."
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="solution">Solution Breakdown (if any)</label>
            <textarea
              id="solution"
              value={solution}
              onChange={(e) => setSolution(e.target.value)}
              rows={4}
              placeholder="Enter the solution breakdown/steps for the base question..."
            />
          </div>
          
          <div style={{ display: 'flex', gap: '20px', alignItems: 'flex-end' }}>
            <div className="form-group" style={{ flex: '1', maxWidth: '200px' }}>
              <label htmlFor="numCopyQuestions">Number of Copy Questions *</label>
              <input
                type="number"
                id="numCopyQuestions"
                value={numCopyQuestions}
                onChange={(e) => {
                  const value = e.target.value
                  if (value === '') {
                    setNumCopyQuestions(1)
                    return
                  }
                  const numValue = parseInt(value, 10)
                  if (!isNaN(numValue)) {
                    if (numValue < 1) {
                      setNumCopyQuestions(1)
                    } else if (numValue > 20) {
                      setNumCopyQuestions(20)
                    } else {
                      setNumCopyQuestions(numValue)
                    }
                  }
                }}
                onBlur={(e) => {
                  const value = parseInt(e.target.value, 10)
                  if (isNaN(value) || value < 1) {
                    setNumCopyQuestions(1)
                  } else if (value > 20) {
                    setNumCopyQuestions(20)
                  }
                }}
                min={1}
                max={20}
                required
                style={{ width: '100%' }}
              />
            </div>
            
            <div className="form-group" style={{ flex: '1', maxWidth: '200px' }}>
            <label htmlFor="model">LLM Model *</label>
            <select
              id="model"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              required
                style={{ width: '100%' }}
            >
                <optgroup label="NaraRouter">
                  <option value="agnes-3-flash">Agnes 3 Flash (Vision)</option>
                  <option value="agnes-2.5-flash">Agnes 2.5 Flash (Vision)</option>
                  <option value="gemini-3.8-flash-high">Gemini 3.8 Flash High (Vision)</option>
                  <option value="gemini-3.1-pro-high">Gemini 3.1 Pro High (Vision)</option>
                  <option value="space-bunny-alpha">Space Bunny Alpha (Vision, Free)</option>
                  <option value="qwen3.8-flash">Qwen 3.8 Flash (Vision)</option>
                  <option value="nemotron-3.5-lightning-free">Nemotron 3.5 Lightning (Free, Text)</option>
                </optgroup>
                <optgroup label="OpenAI">
                  <option value="o3">O3</option>
                  <option value="o4-mini">O4 Mini</option>
                  <option value="gpt-5">GPT-5</option>
                  <option value="gpt-4o">GPT-4o</option>
                </optgroup>
                <optgroup label="Google Gemini">
                  <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                  <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                </optgroup>
            </select>
            </div>
          </div>
          
          <div className="button-group" style={{ flexDirection: 'column', gap: '10px' }}>
            <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%' }}>
              Generate Questions
            </button>
            <div style={{ display: 'flex', gap: '10px', width: '100%' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={copySelected}
              disabled={selectedQuestions.size === 0 || loading}
                style={{ 
                  flex: '1',
                  backgroundColor: copiedSelected ? '#28a745' : undefined,
                  color: copiedSelected ? '#fff' : undefined,
                  borderColor: copiedSelected ? '#28a745' : undefined,
                  transition: 'all 0.3s ease'
                }}
            >
              Copy Selected ({selectedQuestions.size})
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={copyAll}
              disabled={questions.length === 0 || loading}
                style={{ 
                  flex: '1',
                  backgroundColor: copiedAll ? '#28a745' : undefined,
                  color: copiedAll ? '#fff' : undefined,
                  borderColor: copiedAll ? '#28a745' : undefined,
                  transition: 'all 0.3s ease'
                }}
            >
              Copy All Questions
            </button>
            </div>
          </div>
        </form>
        
        {loading && (
          <div className="loading">
            <p>{loadingText || 'Generating questions...'}</p>
          </div>
        )}
        
        {error && (
          <div className="error">
            {error}
          </div>
        )}

        {verificationMessage && (
          <div 
            className="verification-message" 
            style={{
              position: 'fixed',
              top: '20px',
              right: '20px',
              backgroundColor: verificationMessage.type === 'success' ? '#d4edda' : '#f8d7da',
              border: `1px solid ${verificationMessage.type === 'success' ? '#c3e6cb' : '#f5c6cb'}`,
              color: verificationMessage.type === 'success' ? '#155724' : '#721c24',
              padding: '15px 20px',
              borderRadius: '4px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
              maxWidth: '500px',
              zIndex: 10000,
              whiteSpace: 'pre-line',
              fontSize: '14px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '10px' }}>
              <div style={{ flex: 1 }}>
                <strong>{verificationMessage.type === 'success' ? '✓ Verification Complete' : '✗ Verification Failed'}</strong>
                <div style={{ marginTop: '8px' }}>{verificationMessage.message}</div>
              </div>
              <button
                onClick={() => setVerificationMessage(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '20px',
                  cursor: 'pointer',
                  color: 'inherit',
                  padding: '0',
                  lineHeight: '1',
                  opacity: 0.7
                }}
                onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                onMouseLeave={(e) => e.currentTarget.style.opacity = '0.7'}
              >
                ×
              </button>
            </div>
          </div>
        )}
        
        {questions.length > 0 && (
          <div className="results">
            <h2>Generated Copy Questions</h2>
            <div className="questions-container">
              {questions.map((question, index) => (
                <div key={index} className="question-card">
                  <div className="question-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <input
                        type="checkbox"
                        checked={selectedQuestions.has(index)}
                        onChange={() => toggleSelection(index)}
                      />
                      <span className="question-number">Question {index + 1}</span>
                      {question.evalStatus && (
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 600,
                            padding: '2px 8px',
                            borderRadius: '12px',
                            backgroundColor: question.evalStatus.passed ? '#e6f4ea' : '#fef7e0',
                            color: question.evalStatus.passed ? '#137333' : '#b06000',
                            border: `1px solid ${question.evalStatus.passed ? '#ceead6' : '#fdd663'}`,
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px'
                          }}
                          title={question.evalStatus.issues && question.evalStatus.issues.length > 0 ? question.evalStatus.issues.join('; ') : 'All format, option integrity, and SME checks passed.'}
                        >
                          {question.evalStatus.passed ? '✓ Evaluated (100%)' : `⚠ Audit Alert (${question.evalStatus.score}%)`}
                        </span>
                      )}
                    </div>
                    <div className="button-group-inline">
                      <button
                        className="btn btn-secondary"
                        onClick={() => verifyQuestion(index)}
                        disabled={verifyingQuestions.has(index)}
                        style={{
                          backgroundColor: verifyingQuestions.has(index) ? '#ccc' : '#5a2d7a',
                          color: '#fff',
                          marginRight: '8px'
                        }}
                      >
                        {verifyingQuestions.has(index) ? 'Verifying...' : '✓ Verify'}
                      </button>
                      <button
                        className="btn btn-secondary"
                        onClick={() => copyQuestion(index)}
                        style={{
                          backgroundColor: copiedQuestionIndex === index ? '#28a745' : undefined,
                          color: copiedQuestionIndex === index ? '#fff' : undefined,
                          borderColor: copiedQuestionIndex === index ? '#28a745' : undefined,
                          transition: 'all 0.3s ease'
                        }}
                      >
                        Copy
                      </button>
                    </div>
                  </div>
                  <div className="question-text">{question.question}</div>
                  {question.image && (() => {
                    const chartInfo = parseChartFromDescription(question.image)
                    
                    if (chartInfo && chartInfo.chartType) {
                      // Render chart visually
                      return (
                        <div className="image-description" style={{
                          marginTop: '12px',
                          padding: '10px',
                          backgroundColor: '#e3f2fd',
                          borderRadius: '4px',
                          border: '1px solid #90caf9',
                          fontSize: '14px',
                          color: '#555'
                        }}>
                          <strong>Image Description:</strong> {chartInfo.title && <span style={{ fontStyle: 'italic' }}>"{chartInfo.title}"</span>}
                          {renderChart(chartInfo as { chartType: 'bar' | 'line' | 'dot' | 'scatter' | 'histogram', chartData: Array<{name: string, value: number, label?: string}>, title: string, xAxisLabel: string, yAxisLabel: string })}
                        </div>
                      )
                    } else {
                      // Render as HTML (for tables or other content)
                      return (
                        <div className="image-description" style={{
                          marginTop: '12px',
                          padding: '10px',
                          backgroundColor: '#e3f2fd',
                          borderRadius: '4px',
                          border: '1px solid #90caf9',
                          fontSize: '14px',
                          color: '#555',
                          fontStyle: 'italic'
                        }}>
                          <strong>Image Description:</strong>{' '}
                          <span dangerouslySetInnerHTML={{ 
                            __html: DOMPurify.sanitize(question.image, {
                              ALLOWED_TAGS: ['table', 'tr', 'td', 'th', 'thead', 'tbody', 'tfoot'],
                              ALLOWED_ATTR: ['style', 'class', 'colspan', 'rowspan']
                            })
                          }} />
                        </div>
                      )
                    }
                  })()}
                  {question.options && question.options.length > 0 && (
                    <>
                      <h3 className="options-heading">Options</h3>
                      <ul className="options-list">
                        {question.options.map((option, optIndex) => {
                          const isCorrect = option.logic === 'CA'
                          return (
                            <li key={optIndex} className={isCorrect ? 'correct' : 'incorrect'}>
                              <span className="option-label">
                                {String.fromCharCode(65 + optIndex)})
                              </span>
                              <div>
                                <div>{option.text}</div>
                                <div className="option-logic">
                                  Logic: {option.logic}
                                </div>
                              </div>
                            </li>
                          )
                        })}
                      </ul>
                    </>
                  )}
                  {question.solution && (
                    <div className="solution-container">
                      <h3 className="solution-title">Solution:</h3>
                      <div 
                        className="solution-text" 
                        style={{
                          whiteSpace: 'pre-line',
                          lineHeight: '1.8',
                          padding: '12px',
                          backgroundColor: '#f8f9fa',
                          borderRadius: '4px',
                          border: '1px solid #e0e0e0'
                        }}
                      >
                        {(() => {
                          // First, replace literal \n strings with actual newlines if they exist
                          let solutionText = question.solution.replace(/\\n/g, '\n')
                          
                          // Split by newlines
                          let lines = solutionText.split(/\n+/)
                          
                          // If we only have one line but it contains "Step", try to split by "Step" pattern
                          if (lines.length === 1 && /Step\s*\d+/i.test(solutionText)) {
                            // Split by "Step" pattern to separate steps even if no newlines
                            lines = solutionText.split(/(?=Step\s*\d+)/i).filter(line => line.trim())
                          }
                          
                          return lines.map((line, idx) => {
                            const trimmedLine = line.trim()
                            if (!trimmedLine) return <br key={idx} />
                            
                            // Check if it's a step (Step 1:, Step 2:, 1., 2., etc.)
                            const isStep = /^(Step\s*\d+|^\d+\.|^[A-Z]\.)/i.test(trimmedLine)
                            
                            return (
                              <div 
                                key={idx} 
                                style={{
                                  marginBottom: isStep ? '8px' : '4px',
                                  fontWeight: isStep ? '600' : '400',
                                  color: isStep ? '#5a2d7a' : '#333'
                                }}
                              >
                                {trimmedLine}
                              </div>
                            )
                          })
                        })()}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Table Builder Modal */}
        {showTableBuilder && (
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000,
              padding: '20px'
            }}
            onClick={() => setShowTableBuilder(false)}
          >
            <div
              style={{
                backgroundColor: 'white',
                borderRadius: '12px',
                padding: '30px',
                maxHeight: '90vh',
                overflow: 'auto',
                boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
                width: '100%',
                maxWidth: '800px'
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2 style={{ margin: 0, color: '#5a2d7a' }}>📊 Table Builder</h2>
                <button
                  onClick={() => {
                    setShowTableBuilder(false)
                    resetTableBuilder()
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    fontSize: '24px',
                    cursor: 'pointer',
                    color: '#666',
                    padding: '0',
                    lineHeight: '1'
                  }}
                >
                  ×
                </button>
              </div>
              
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
                  <input
                    type="checkbox"
                    checked={hasHeader}
                    onChange={(e) => setHasHeader(e.target.checked)}
                  />
                  <span>First row is header</span>
                </label>
              </div>
              
              <div style={{ marginBottom: '20px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={addTableRow}
                  className="btn btn-secondary"
                  style={{ fontSize: '14px', padding: '8px 16px' }}
                >
                  + Add Row
                </button>
                <button
                  type="button"
                  onClick={removeTableRow}
                  className="btn btn-secondary"
                  disabled={tableData.rows <= 1}
                  style={{ fontSize: '14px', padding: '8px 16px' }}
                >
                  - Remove Row
                </button>
                <button
                  type="button"
                  onClick={addTableColumn}
                  className="btn btn-secondary"
                  style={{ fontSize: '14px', padding: '8px 16px' }}
                >
                  + Add Column
                </button>
                <button
                  type="button"
                  onClick={removeTableColumn}
                  className="btn btn-secondary"
                  disabled={tableData.cols <= 1}
                  style={{ fontSize: '14px', padding: '8px 16px' }}
                >
                  - Remove Column
                </button>
              </div>
              
              <div style={{ marginBottom: '20px', overflowX: 'auto' }}>
                <table
                  style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    border: '2px solid #5a2d7a'
                  }}
                >
                  <tbody>
                    {tableData.data.map((row, rowIndex) => (
                      <tr key={rowIndex}>
                        {row.map((cell, colIndex) => {
                          const isHeaderCell = hasHeader && rowIndex === 0
                          return (
                            <td
                              key={colIndex}
                              style={{
                                border: '1px solid #ddd',
                                padding: '8px',
                                backgroundColor: isHeaderCell ? '#f0f0f0' : 'white',
                                fontWeight: isHeaderCell ? 'bold' : 'normal'
                              }}
                            >
                              <input
                                type="text"
                                value={cell}
                                onChange={(e) => updateTableCell(rowIndex, colIndex, e.target.value)}
                                placeholder={isHeaderCell ? 'Header' : 'Cell'}
                                style={{
                                  width: '100%',
                                  border: 'none',
                                  outline: 'none',
                                  padding: '4px',
                                  fontSize: '14px',
                                  backgroundColor: 'transparent'
                                }}
                              />
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
                <strong style={{ display: 'block', marginBottom: '10px' }}>Preview:</strong>
                <div
                  style={{
                    fontSize: '12px',
                    color: '#666',
                    fontFamily: 'monospace',
                    whiteSpace: 'pre-wrap',
                    maxHeight: '150px',
                    overflow: 'auto'
                  }}
                >
                  {convertTableToHTML()}
                </div>
              </div>
              
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => {
                    setShowTableBuilder(false)
                    resetTableBuilder()
                  }}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={insertTableIntoImageDescription}
                  className="btn btn-primary"
                >
                  Insert Table
                </button>
              </div>
            </div>
          </div>
        )}
        
        {/* Chart Builder Modal */}
        {showChartBuilder && (
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000,
              padding: '20px'
            }}
            onClick={() => setShowChartBuilder(false)}
          >
            <div
              style={{
                backgroundColor: 'white',
                borderRadius: '12px',
                padding: '30px',
                maxHeight: '90vh',
                overflow: 'auto',
                boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
                width: '100%',
                maxWidth: '900px'
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2 style={{ margin: 0, color: '#5a2d7a' }}>📈 Chart Builder</h2>
                <button
                  onClick={() => {
                    setShowChartBuilder(false)
                    resetChartBuilder()
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    fontSize: '24px',
                    cursor: 'pointer',
                    color: '#666',
                    padding: '0',
                    lineHeight: '1'
                  }}
                >
                  ×
                </button>
              </div>
              
              {/* Chart Type Selection */}
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Chart Type</label>
                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                  {(['bar', 'line', 'dot', 'scatter'] as const).map(type => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => setChartType(type)}
                      style={{
                        padding: '8px 16px',
                        fontSize: '14px',
                        fontWeight: '600',
                        backgroundColor: chartType === type ? '#5a2d7a' : '#fff',
                        color: chartType === type ? '#fff' : '#5a2d7a',
                        border: '1px solid #5a2d7a',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        textTransform: 'capitalize'
                      }}
                    >
                      {type === 'dot' ? 'Dot Plot' : type === 'scatter' ? 'Scatter Plot' : type === 'bar' ? 'Bar Chart' : 'Line Graph'}
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Chart Labels */}
              <div style={{ marginBottom: '20px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Chart Title (optional)</label>
                  <input
                    type="text"
                    value={chartTitle}
                    onChange={(e) => setChartTitle(e.target.value)}
                    placeholder="e.g., Sales by Month"
                    style={{
                      width: '100%',
                      padding: '8px',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      fontSize: '14px'
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>X-Axis Label (optional)</label>
                  <input
                    type="text"
                    value={xAxisLabel}
                    onChange={(e) => setXAxisLabel(e.target.value)}
                    placeholder="e.g., Month"
                    style={{
                      width: '100%',
                      padding: '8px',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      fontSize: '14px'
                    }}
                  />
                </div>
                {chartType !== 'dot' && (
                  <div>
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Y-Axis Label (optional)</label>
                    <input
                      type="text"
                      value={yAxisLabel}
                      onChange={(e) => setYAxisLabel(e.target.value)}
                      placeholder="e.g., Sales ($)"
                      style={{
                        width: '100%',
                        padding: '8px',
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        fontSize: '14px'
                      }}
                    />
                  </div>
                )}
                {chartType !== 'dot' && (
                  <>
                    <div>
                      <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Y-Axis Min (optional)</label>
                      <input
                        type="number"
                        value={yAxisMin ?? ''}
                        onChange={(e) => setYAxisMin(e.target.value ? parseFloat(e.target.value) : undefined)}
                        placeholder="Auto"
                        style={{
                          width: '100%',
                          padding: '8px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          fontSize: '14px'
                        }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Y-Axis Max (optional)</label>
                      <input
                        type="number"
                        value={yAxisMax ?? ''}
                        onChange={(e) => setYAxisMax(e.target.value ? parseFloat(e.target.value) : undefined)}
                        placeholder="Auto"
                        style={{
                          width: '100%',
                          padding: '8px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          fontSize: '14px'
                        }}
                      />
                    </div>
                  </>
                )}
              </div>
              
              {/* Chart Preview */}
              <div style={{ marginBottom: '20px', padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
                <strong style={{ display: 'block', marginBottom: '15px' }}>Preview:</strong>
                <div style={{ width: '100%', height: '300px' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    {chartType === 'bar' ? (
                      <BarChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" label={xAxisLabel ? { value: xAxisLabel, position: 'insideBottom', offset: -5 } : undefined} />
                        <YAxis 
                          label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft' } : undefined}
                          domain={yAxisMin !== undefined || yAxisMax !== undefined ? [yAxisMin ?? 'auto', yAxisMax ?? 'auto'] : undefined}
                        />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="value" fill="#5a2d7a" />
                      </BarChart>
                    ) : chartType === 'line' ? (
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" label={xAxisLabel ? { value: xAxisLabel, position: 'insideBottom', offset: -5 } : undefined} />
                        <YAxis 
                          label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft' } : undefined}
                          domain={yAxisMin !== undefined || yAxisMax !== undefined ? [yAxisMin ?? 'auto', yAxisMax ?? 'auto'] : undefined}
                        />
                        <Tooltip />
                        <Legend />
                        <Line type="monotone" dataKey="value" stroke="#5a2d7a" strokeWidth={2} />
                      </LineChart>
                    ) : chartType === 'dot' ? (
                      <ScatterChart
                        margin={{ top: 20, right: 20, bottom: 40, left: 20 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis 
                          type="number"
                          dataKey="x" 
                          name={xAxisLabel || 'x'} 
                          label={xAxisLabel ? { value: xAxisLabel, position: 'insideBottom', offset: -5 } : undefined}
                          domain={[-0.5, chartData.length - 0.5]}
                          ticks={chartData.map((_, i) => i)}
                          tickFormatter={(value) => {
                            // Find the original name for this x value
                            const index = Math.round(value)
                            const dataPoint = chartData[index]
                            return dataPoint ? dataPoint.name : ''
                          }}
                        />
                        <YAxis 
                          type="number"
                          domain={[0, 'dataMax + 1']}
                          hide={true}
                        />
                        <Tooltip 
                          cursor={{ strokeDasharray: '3 3' }}
                          formatter={(value: any, name: any, props: any) => {
                            return [`${props.payload.originalValue} dot${props.payload.originalValue !== 1 ? 's' : ''}`, 'Count']
                          }}
                        />
                        <Scatter 
                          data={chartData.flatMap((d, i) => {
                            const xValue = i // Use index as x position for even spacing
                            const yValue = Math.max(0, Math.round(d.value)) // Ensure integer value and non-negative
                            // Create multiple dots stacked vertically (1 dot per y-value) above x-axis
                            return Array.from({ length: yValue }, (_, dotIndex) => ({
                              x: xValue,
                              y: dotIndex + 1, // Stack dots from 1 upward (above x-axis at y=0)
                              originalValue: yValue,
                              name: d.name
                            }))
                          })} 
                          fill="#5a2d7a"
                          shape={(props: any) => {
                            const { cx, cy, payload } = props
                            if (cx == null || cy == null || typeof cx !== 'number' || typeof cy !== 'number') {
                              return <g />
                            }
                            return (
                              <circle 
                                cx={cx} 
                                cy={cy} 
                                r={6} 
                                fill="#5a2d7a" 
                                stroke="#5a2d7a"
                                strokeWidth={1}
                              />
                            )
                          }}
                          dataKey="y"
                        />
                      </ScatterChart>
                    ) : (
                      <ScatterChart>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis type="number" dataKey="x" name={xAxisLabel || 'x'} label={xAxisLabel ? { value: xAxisLabel, position: 'insideBottom', offset: -5 } : undefined} />
                        <YAxis 
                          type="number" 
                          dataKey="y" 
                          name={yAxisLabel || 'y'} 
                          label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft' } : undefined}
                          domain={yAxisMin !== undefined || yAxisMax !== undefined ? [yAxisMin ?? 'auto', yAxisMax ?? 'auto'] : undefined}
                        />
                        <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                        <Scatter data={chartData.map((d, i) => ({ x: parseFloat(d.name) || i, y: d.value }))} fill="#5a2d7a" />
                      </ScatterChart>
                    )}
                  </ResponsiveContainer>
                </div>
              </div>
              
              {/* Data Points Editor */}
              <div style={{ marginBottom: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <strong>Data Points</strong>
                  <button
                    type="button"
                    onClick={addChartDataPoint}
                    className="btn btn-secondary"
                    style={{ fontSize: '14px', padding: '6px 12px' }}
                  >
                    + Add Point
                  </button>
                </div>
                <div style={{ maxHeight: '200px', overflowY: 'auto', border: '1px solid #ddd', borderRadius: '4px', padding: '10px' }}>
                  {chartData.map((point, index) => (
                    <div key={index} style={{ display: 'flex', gap: '10px', marginBottom: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                      <input
                        type="text"
                        value={point.name}
                        onChange={(e) => updateChartDataPoint(index, 'name', e.target.value)}
                        placeholder={chartType === 'dot' || chartType === 'scatter' ? 'x value' : 'Category'}
                        style={{
                          flex: '1',
                          minWidth: '100px',
                          padding: '6px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          fontSize: '14px'
                        }}
                      />
                      <input
                        type="number"
                        value={point.value}
                        onChange={(e) => updateChartDataPoint(index, 'value', parseFloat(e.target.value) || 0)}
                        placeholder={chartType === 'dot' ? 'Number of dots' : chartType === 'scatter' ? 'y value' : 'Value'}
                        style={{
                          flex: '1',
                          minWidth: '100px',
                          padding: '6px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          fontSize: '14px'
                        }}
                      />
                      {(chartType === 'dot' || chartType === 'scatter') && (
                        <input
                          type="text"
                          value={point.label || ''}
                          onChange={(e) => updateChartDataPoint(index, 'label', e.target.value)}
                          placeholder="Label (optional)"
                          style={{
                            flex: '1',
                            minWidth: '100px',
                            padding: '6px',
                            border: '1px solid #ddd',
                            borderRadius: '4px',
                            fontSize: '14px'
                          }}
                        />
                      )}
                      <button
                        type="button"
                        onClick={() => removeChartDataPoint(index)}
                        disabled={chartData.length <= 1}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: chartData.length > 1 ? '#ff4444' : '#ccc',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: chartData.length > 1 ? 'pointer' : 'not-allowed',
                          fontSize: '14px'
                        }}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              </div>
              
              {/* HTML Preview */}
              <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
                <strong style={{ display: 'block', marginBottom: '10px' }}>Generated Description:</strong>
                <div
                  style={{
                    fontSize: '12px',
                    color: '#666',
                    fontFamily: 'monospace',
                    whiteSpace: 'pre-wrap',
                    maxHeight: '150px',
                    overflow: 'auto',
                    padding: '10px',
                    backgroundColor: 'white',
                    borderRadius: '4px',
                    border: '1px solid #ddd'
                  }}
                >
                  {convertChartToHTML()}
                </div>
              </div>
              
              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => {
                    setShowChartBuilder(false)
                    resetChartBuilder()
                  }}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={insertChartIntoImageDescription}
                  className="btn btn-primary"
                >
                  Insert Chart Description
                </button>
              </div>
            </div>
          </div>
        )}
        
        {/* Shape Builder Modal */}
        {showShapeBuilder && (
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000,
              padding: '20px'
            }}
            onClick={() => setShowShapeBuilder(false)}
          >
            <div
              style={{
                backgroundColor: 'white',
                borderRadius: '12px',
                padding: '30px',
                maxHeight: '90vh',
                overflow: 'auto',
                boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
                width: '100%',
                maxWidth: '900px'
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2 style={{ margin: 0, color: '#5a2d7a' }}>🔷 Geometric Shape Builder</h2>
                <button
                  onClick={() => {
                    setShowShapeBuilder(false)
                    resetShapeBuilder()
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    fontSize: '24px',
                    cursor: 'pointer',
                    color: '#666',
                    padding: '0',
                    lineHeight: '1'
                  }}
                >
                  ×
                </button>
              </div>
              
              {/* Shape Type Selection */}
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Shape Type</label>
                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                  {(['triangle', 'circle', 'rectangle', 'polygon'] as const).map(type => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => setShapeType(type)}
                      style={{
                        padding: '8px 16px',
                        fontSize: '14px',
                        fontWeight: '600',
                        backgroundColor: shapeType === type ? '#5a2d7a' : '#fff',
                        color: shapeType === type ? '#fff' : '#5a2d7a',
                        border: '1px solid #5a2d7a',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        textTransform: 'capitalize'
                      }}
                    >
                      {type === 'triangle' ? 'Triangle' : type === 'circle' ? 'Circle' : type === 'rectangle' ? 'Rectangle' : 'Polygon'}
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Shape-Specific Inputs */}
              <div style={{ marginBottom: '20px' }}>
                {shapeType === 'triangle' && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                    <div>
                      <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Side A (cm)</label>
                      <input
                        type="number"
                        value={shapeData.sideA || ''}
                        onChange={(e) => updateShapeData('sideA', parseFloat(e.target.value) || 0)}
                        style={{
                          width: '100%',
                          padding: '8px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          fontSize: '14px'
                        }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Side B (cm)</label>
                      <input
                        type="number"
                        value={shapeData.sideB || ''}
                        onChange={(e) => updateShapeData('sideB', parseFloat(e.target.value) || 0)}
                        style={{
                          width: '100%',
                          padding: '8px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          fontSize: '14px'
                        }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Side C (cm)</label>
                      <input
                        type="number"
                        value={shapeData.sideC || ''}
                        onChange={(e) => updateShapeData('sideC', parseFloat(e.target.value) || 0)}
                        style={{
                          width: '100%',
                          padding: '8px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          fontSize: '14px'
                        }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Triangle Type</label>
                      <select
                        value={shapeData.type || 'scalene'}
                        onChange={(e) => updateShapeData('type', e.target.value)}
                        style={{
                          width: '100%',
                          padding: '8px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          fontSize: '14px'
                        }}
                      >
                        <option value="right">Right</option>
                        <option value="equilateral">Equilateral</option>
                        <option value="isosceles">Isosceles</option>
                        <option value="scalene">Scalene</option>
                      </select>
                    </div>
                    <div>
                      <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Angle A (°)</label>
                      <input
                        type="number"
                        value={shapeData.angleA || ''}
                        onChange={(e) => updateShapeData('angleA', parseFloat(e.target.value) || 0)}
                        style={{
                          width: '100%',
                          padding: '8px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          fontSize: '14px'
                        }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Angle B (°)</label>
                      <input
                        type="number"
                        value={shapeData.angleB || ''}
                        onChange={(e) => updateShapeData('angleB', parseFloat(e.target.value) || 0)}
                        style={{
                          width: '100%',
                          padding: '8px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          fontSize: '14px'
                        }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Angle C (°)</label>
                      <input
                        type="number"
                        value={shapeData.angleC || ''}
                        onChange={(e) => updateShapeData('angleC', parseFloat(e.target.value) || 0)}
                        style={{
                          width: '100%',
                          padding: '8px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          fontSize: '14px'
                        }}
                      />
                    </div>
                    {validateTriangle() && (
                      <div style={{ gridColumn: '1 / -1', padding: '10px', backgroundColor: '#ffebee', borderRadius: '4px', border: '1px solid #f44336' }}>
                        <span style={{ color: '#c62828', fontSize: '14px' }}>⚠️ {validateTriangle()}</span>
                      </div>
                    )}
                  </div>
                )}
                
                {shapeType === 'circle' && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                    <div>
                      <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Radius (cm)</label>
                      <input
                        type="number"
                        value={shapeData.radius || ''}
                        onChange={(e) => {
                          const r = parseFloat(e.target.value) || 0
                          updateShapeData('radius', r)
                          updateShapeData('diameter', r * 2)
                        }}
                        style={{
                          width: '100%',
                          padding: '8px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          fontSize: '14px'
                        }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Diameter (cm)</label>
                      <input
                        type="number"
                        value={shapeData.diameter || ''}
                        onChange={(e) => {
                          const d = parseFloat(e.target.value) || 0
                          updateShapeData('diameter', d)
                          updateShapeData('radius', d / 2)
                        }}
                        style={{
                          width: '100%',
                          padding: '8px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          fontSize: '14px'
                        }}
                      />
                    </div>
                  </div>
                )}
                
                {shapeType === 'rectangle' && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                    <div>
                      <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Width (cm)</label>
                      <input
                        type="number"
                        value={shapeData.width || ''}
                        onChange={(e) => updateShapeData('width', parseFloat(e.target.value) || 0)}
                        style={{
                          width: '100%',
                          padding: '8px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          fontSize: '14px'
                        }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Height (cm)</label>
                      <input
                        type="number"
                        value={shapeData.height || ''}
                        onChange={(e) => updateShapeData('height', parseFloat(e.target.value) || 0)}
                        style={{
                          width: '100%',
                          padding: '8px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          fontSize: '14px'
                        }}
                      />
                    </div>
                  </div>
                )}
                
                {shapeType === 'polygon' && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                    <div>
                      <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Number of Sides</label>
                      <input
                        type="number"
                        min="3"
                        max="12"
                        value={shapeData.sides || ''}
                        onChange={(e) => updateShapeData('sides', parseInt(e.target.value) || 3)}
                        style={{
                          width: '100%',
                          padding: '8px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          fontSize: '14px'
                        }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>Side Length (cm)</label>
                      <input
                        type="number"
                        value={shapeData.sideLength || ''}
                        onChange={(e) => updateShapeData('sideLength', parseFloat(e.target.value) || 0)}
                        style={{
                          width: '100%',
                          padding: '8px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          fontSize: '14px'
                        }}
                      />
                    </div>
                    <div style={{ gridColumn: '1 / -1' }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                        <input
                          type="checkbox"
                          checked={shapeData.isRegular !== false}
                          onChange={(e) => updateShapeData('isRegular', e.target.checked)}
                        />
                        <span style={{ fontWeight: '600' }}>Regular Polygon (all sides and angles equal)</span>
                      </label>
                    </div>
                  </div>
                )}
              </div>
              
              {/* Shape Preview */}
              <div style={{ marginBottom: '20px', padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '8px', display: 'flex', justifyContent: 'center' }}>
                {renderShapeSVG()}
              </div>
              
              {/* Generated Description Preview */}
              <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
                <strong style={{ display: 'block', marginBottom: '10px' }}>Generated Description:</strong>
                <div
                  style={{
                    fontSize: '12px',
                    color: '#666',
                    fontFamily: 'monospace',
                    whiteSpace: 'pre-wrap',
                    maxHeight: '150px',
                    overflow: 'auto',
                    padding: '10px',
                    backgroundColor: 'white',
                    borderRadius: '4px',
                    border: '1px solid #ddd'
                  }}
                >
                  {convertShapeToHTML()}
                </div>
              </div>
              
              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => {
                    setShowShapeBuilder(false)
                    resetShapeBuilder()
                  }}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={insertShapeIntoImageDescription}
                  className="btn btn-primary"
                  disabled={!!validateTriangle()}
                  style={{
                    opacity: validateTriangle() ? 0.5 : 1,
                    cursor: validateTriangle() ? 'not-allowed' : 'pointer'
                  }}
                >
                  Insert Shape Description
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default function GeneratePage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <GeneratePageContent />
    </Suspense>
  )
}

