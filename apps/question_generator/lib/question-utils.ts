export function parseNumberOfOptions(baseQuestion: string): number {
  const foundOptions = new Set<string>()
  
  // Pattern 1: A), B), C), D) - letter followed by closing paren and space
  const pattern1 = /\b([A-Z])\)\s/gi
  const matches1 = Array.from(baseQuestion.matchAll(pattern1))
  for (const match of matches1) {
    foundOptions.add(match[1].toUpperCase())
  }
  
  // Pattern 2: A. B. C. D. - letter followed by period and space
  const pattern2 = /\b([A-Z])\.\s/gi
  const matches2 = Array.from(baseQuestion.matchAll(pattern2))
  for (const match of matches2) {
    foundOptions.add(match[1].toUpperCase())
  }
  
  // Pattern 3: (A), (B), (C), (D) - letter in parentheses
  const pattern3 = /\(([A-Z])\)/gi
  const matches3 = Array.from(baseQuestion.matchAll(pattern3))
  for (const match of matches3) {
    foundOptions.add(match[1].toUpperCase())
  }
  
  // Pattern 4: Option A, Option B, Option C, Option D
  const pattern4 = /Option\s+([A-Z])[:\s]/gi
  const matches4 = Array.from(baseQuestion.matchAll(pattern4))
  for (const match of matches4) {
    foundOptions.add(match[1].toUpperCase())
  }
  
  // Pattern 5: A) Text, B) Text (no space after paren)
  const pattern5 = /\b([A-Z])\)[^\s]/gi
  const matches5 = Array.from(baseQuestion.matchAll(pattern5))
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
    const matches = Array.from(baseQuestion.matchAll(pattern))
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

export function determineQuestionType(baseQuestion: string, notes?: string): 'word_problem' | 'mathematical' {
  const wordProblemKeywords = [
    'bought', 'sold', 'store', 'park', 'school', 'restaurant',
    'recipe', 'shopping', 'travel', 'distance', 'speed', 'time',
    'age', 'people', 'students', 'teacher', 'class'
  ]
  
  const questionLower = baseQuestion.toLowerCase()
  let hasContext = wordProblemKeywords.some(keyword => questionLower.includes(keyword))
  
  if (notes && (notes.toLowerCase().includes('context') || notes.toLowerCase().includes('real-life'))) {
    hasContext = true
  }
  
  return hasContext ? 'word_problem' : 'mathematical'
}

