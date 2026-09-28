import OpenAI from 'openai'

export function getNaraRouterClient(): OpenAI {
  const apiKey = process.env.NARAROUTER_API_KEY
  if (!apiKey || apiKey === 'your_nararouter_api_key_here') {
    throw new Error('Please set your NARAROUTER_API_KEY in the .env.local file')
  }
  const baseURL = process.env.NARAROUTER_BASE_URL || 'https://router.bynara.id/v1'
  return new OpenAI({
    apiKey,
    baseURL,
  })
}

export const NARA_ROUTER_MODELS = [
  { id: 'agnes-3-flash', name: 'Agnes 3 Flash (Vision)', vision: true },
  { id: 'agnes-2.5-flash', name: 'Agnes 2.5 Flash (Vision)', vision: true },
  { id: 'gemini-3.8-flash-high', name: 'Gemini 3.8 Flash High (Vision)', vision: true },
  { id: 'gemini-3.1-pro-high', name: 'Gemini 3.1 Pro High (Vision)', vision: true },
  { id: 'space-bunny-alpha', name: 'Space Bunny Alpha (Vision, Free)', vision: true },
  { id: 'qwen3.8-flash', name: 'Qwen 3.8 Flash (Vision)', vision: true },
  { id: 'deepseek-v4.1-flash', name: 'DeepSeek v4.1 Flash (Vision)', vision: true },
  { id: 'nemotron-3.5-lightning-free', name: 'Nemotron 3.5 Lightning (Free, Text)', vision: false },
]

export function isNaraRouterModel(model: string): boolean {
  return (
    model.startsWith('agnes-') ||
    model.startsWith('space-bunny-') ||
    model.startsWith('nemotron-') ||
    model.startsWith('ling-3.0-') ||
    model.startsWith('laguna-') ||
    model.startsWith('mimo-') ||
    model.startsWith('qwen3.8-') ||
    model.startsWith('deepseek-') ||
    model.endsWith('-high') || // gemini-3.8-flash-high, gemini-3.1-pro-high from NaraRouter
    NARA_ROUTER_MODELS.some(m => m.id === model)
  )
}

export function doesNaraModelSupportVision(model: string): boolean {
  const found = NARA_ROUTER_MODELS.find(m => m.id === model)
  if (found) return found.vision
  return (
    model.includes('flash') ||
    model.includes('vision') ||
    model.includes('pro') ||
    model.startsWith('agnes-') ||
    model.startsWith('space-bunny-')
  )
}
