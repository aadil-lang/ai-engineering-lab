import { getOpenAIClient, analyzeImageForQuestion as analyzeImageWithOpenAI } from './openai'
import { getGeminiClient, isGeminiModel, generateWithGemini, analyzeImageWithGemini } from './gemini'
import { getNaraRouterClient, isNaraRouterModel, doesNaraModelSupportVision } from './nararouter'

export type AIModel = string
export type AIProvider = 'openai' | 'gemini' | 'nararouter'

export function getAIProvider(model: string): AIProvider {
  if (isGeminiModel(model)) {
    return 'gemini'
  }
  if (isNaraRouterModel(model)) {
    return 'nararouter'
  }
  return 'openai'
}

export async function generateWithAI(
  systemPrompt: string,
  userPrompt: string,
  model: string,
  temperature: number = 0.7,
  maxTokens: number = 8000,
  imageFiles?: string[]
): Promise<string> {
  const provider = getAIProvider(model)
  
  if (provider === 'gemini') {
    return generateWithGemini(systemPrompt, userPrompt, model, temperature, maxTokens, imageFiles)
  } else if (provider === 'nararouter') {
    const client = getNaraRouterClient()
    const supportsVision = doesNaraModelSupportVision(model)
    const shouldIncludeImages = imageFiles && imageFiles.length > 0 && supportsVision

    const messages: any[] = [
      { role: 'system', content: systemPrompt },
      shouldIncludeImages
        ? {
            role: 'user',
            content: [
              { type: 'text', text: userPrompt },
              ...imageFiles!.map((img: string) => ({
                type: 'image_url',
                image_url: {
                  url: img.startsWith('data:') ? img : `data:image/jpeg;base64,${img.replace(/^data:image\/[a-z]+;base64,/, '')}`
                }
              }))
            ]
          }
        : { role: 'user', content: userPrompt }
    ]

    const response = await client.chat.completions.create({
      model: model,
      messages: messages,
      max_tokens: maxTokens,
      temperature: temperature,
    })

    if (!response.choices || response.choices.length === 0) {
      throw new Error('NaraRouter returned empty response')
    }

    const content = response.choices[0].message.content
    if (!content || content.trim().length === 0) {
      throw new Error('NaraRouter returned empty content')
    }

    return content
  } else {
    // OpenAI
    const client = getOpenAIClient()
    const supportsVision = model === 'gpt-4o' || model === 'gpt-4-turbo' || model === 'gpt-4-turbo-preview'
    const shouldIncludeImages = imageFiles && imageFiles.length > 0 && supportsVision

    const messages: any[] = [
      { role: 'system', content: systemPrompt },
      shouldIncludeImages
        ? {
            role: 'user',
            content: [
              { type: 'text', text: userPrompt },
              ...imageFiles!.map((img: string) => ({
                type: 'image_url',
                image_url: {
                  url: img.startsWith('data:') ? img : `data:image/jpeg;base64,${img.replace(/^data:image\/[a-z]+;base64,/, '')}`
                }
              }))
            ]
          }
        : { role: 'user', content: userPrompt }
    ]

    const response = await client.chat.completions.create({
      model: model,
      messages: messages,
      max_tokens: maxTokens,
      temperature: temperature,
    })

    if (!response.choices || response.choices.length === 0) {
      throw new Error('AI returned empty response')
    }

    const content = response.choices[0].message.content
    if (!content || content.trim().length === 0) {
      throw new Error('AI returned empty content')
    }

    return content
  }
}

export async function analyzeImageForQuestion(
  imageBase64: string,
  model: string = 'agnes-3-flash'
): Promise<string> {
  const provider = getAIProvider(model)
  
  if (provider === 'gemini') {
    const visionModel = model.startsWith('gemini-') ? model : 'gemini-1.5-pro'
    return analyzeImageWithGemini(imageBase64, visionModel)
  } else if (provider === 'nararouter') {
    const client = getNaraRouterClient()
    const imageUrl = imageBase64.startsWith('data:') 
      ? imageBase64 
      : `data:image/jpeg;base64,${imageBase64.replace(/^data:image\/[a-z]+;base64,/, '')}`
    
    const response = await client.chat.completions.create({
      model: model,
      messages: [
        {
          role: 'system',
          content: 'You are an expert at analyzing mathematical images. Extract all text, numbers, measurements, geometric shapes, graphs, tables, and any mathematical content from the image. Provide a detailed description that can be used to generate questions. Be precise and include all visible information.'
        },
        {
          role: 'user',
          content: [
            {
              type: 'text',
              text: `Analyze this mathematical image and extract all content including:
- All text, numbers, and labels
- Geometric shapes and their measurements (sides, angles, etc.)
- Graphs, coordinates, and data points
- Tables, charts, and their values
- Any mathematical equations or formulas visible
- Colors, line types, and visual annotations
- Scale, units, and reference points

IMPORTANT FOR STRUCTURED DATA:
- If the image contains a TABLE: Present the data in a clear tabular format using HTML table tags
- If the image contains a DOT PLOT or LINE PLOT: Extract the data points and present them in HTML table format with columns for x-values, y-values, and any labels
- If the image contains a BAR CHART or HISTOGRAM: Present the data in HTML table format with categories and values

Provide a comprehensive description that includes all numbers, measurements, labels, and visual elements that would be needed to generate similar questions.`
            },
            {
              type: 'image_url',
              image_url: {
                url: imageUrl
              }
            }
          ]
        }
      ],
      max_tokens: 2000,
      temperature: 0.3
    })
    return response.choices[0]?.message?.content || ''
  } else {
    // OpenAI
    return analyzeImageWithOpenAI(imageBase64, model)
  }
}
