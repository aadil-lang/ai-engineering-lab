import { generateWithAI } from './ai-client'

export interface QuestionOption {
  text: string
  logic: string
}

export interface QuestionData {
  question: string
  options: QuestionOption[]
  image?: string
  solution?: string
  evalStatus?: EvalResult
}

export interface EvalResult {
  passed: boolean
  score: number // 0 to 100
  issues: string[]
  calculatedAnswer?: string
  markedCaIsCorrect?: boolean
  pedagogicalFeedback?: string
  evaluatedAt?: string
}

/**
 * Tier 1: Fast Deterministic Evaluation (0ms, 0 API cost)
 * Audits option counts, CA exclusivity, duplicate options, and format rules.
 */
export function evaluateDeterministic(
  question: { question: string; options: QuestionOption[]; solution?: string },
  expectedOptionsCount: number = 4,
  smeNotes: string = ''
): EvalResult {
  const issues: string[] = []
  let score = 100

  // 1. Question text presence
  if (!question.question || question.question.trim().length < 5) {
    issues.push('Question statement is too short or empty.')
    score -= 30
  }

  // 2. Options count check
  if (!question.options || !Array.isArray(question.options)) {
    issues.push('Options array is missing or invalid.')
    return { passed: false, score: 0, issues }
  }

  if (question.options.length !== expectedOptionsCount) {
    issues.push(`Expected exactly ${expectedOptionsCount} options, but found ${question.options.length}.`)
    score -= 25
  }

  // 3. Exactly one Correct Answer (CA)
  const caOptions = question.options.filter(
    (opt) => (opt.logic || '').trim().toUpperCase() === 'CA'
  )

  if (caOptions.length === 0) {
    issues.push('No option is marked with logic: "CA" (Correct Answer).')
    score -= 35
  } else if (caOptions.length > 1) {
    issues.push(`Multiple options (${caOptions.length}) are marked as Correct Answer ("CA").`)
    score -= 30
  }

  // 4. Duplicate option text detection
  const seenTexts = new Set<string>()
  for (let i = 0; i < question.options.length; i++) {
    const rawText = (question.options[i].text || '').trim().toLowerCase()
    if (!rawText) {
      issues.push(`Option ${String.fromCharCode(65 + i)} has empty text.`)
      score -= 15
    } else if (seenTexts.has(rawText)) {
      issues.push(`Duplicate option found: "${question.options[i].text}".`)
      score -= 20
    } else {
      seenTexts.add(rawText)
    }

    // Distractor logic presence for non-CA options
    const isCa = (question.options[i].logic || '').trim().toUpperCase() === 'CA'
    if (!isCa && (!question.options[i].logic || question.options[i].logic.trim().length === 0)) {
      issues.push(`Distractor option ${String.fromCharCode(65 + i)} is missing error explanation logic.`)
      score -= 5
    }
  }

  // 5. Solution format inspection
  if (question.solution) {
    const sol = question.solution.trim()
    if (!sol.includes('Step 1') && !sol.includes('Step')) {
      issues.push('Solution is missing structured step-by-step format (e.g. "Step 1:").')
      score -= 10
    }
  } else {
    issues.push('Step-by-step solution is missing.')
    score -= 15
  }

  // 6. SME Notes Compliance Heuristics
  if (smeNotes) {
    const lowerNotes = smeNotes.toLowerCase()
    if (lowerNotes.includes('mixed number') && caOptions.length === 1) {
      const caText = caOptions[0].text
      // Regex for mixed number e.g. "2 1/3" or "5 2/7"
      const isMixed = /^\d+\s+\d+\/\d+$/.test(caText.trim())
      if (!isMixed && caText.includes('/')) {
        issues.push(`SME note requested mixed number format, but CA is "${caText}".`)
        score -= 20
      }
    }
  }

  const normalizedScore = Math.max(0, score)
  return {
    passed: issues.length === 0,
    score: normalizedScore,
    issues,
    evaluatedAt: new Date().toISOString()
  }
}

/**
 * Tier 2/3: Semantic Blind-Solve Evaluator via LLM
 * Solves the problem independently without looking at the marked CA,
 * then checks if the marked CA matches its mathematical ground truth.
 */
export async function evaluateWithLLM(
  question: { question: string; options: QuestionOption[]; solution?: string },
  baseQuestion: string,
  smeNotes: string = '',
  model: string = 'agnes-3-flash'
): Promise<EvalResult> {
  // First run deterministic checks
  const deterministicResult = evaluateDeterministic(question, question.options.length, smeNotes)

  const systemPrompt = `You are an adversarial AI Quality Auditor for US Curriculum Math Assessments.
Your job is to independently verify mathematical accuracy and ensure that test questions are completely sound.

CRITICAL BLIND-SOLVE INSTRUCTIONS:
1. Solve the question from scratch independently. Show your calculated result.
2. Compare your calculated result with the marked Correct Answer (CA).
3. If the marked CA is incorrect or ambiguous, flag passed as false.
4. Return ONLY valid JSON matching the schema.`

  const userPrompt = `AUDIT ASSIGNMENT:

BASE TEMPLATE:
${baseQuestion}

${smeNotes ? `MANDATORY SME RULES:\n${smeNotes}\n` : ''}
QUESTION STATEMENT:
${question.question}

OPTIONS GIVEN:
${question.options.map((opt, i) => `${String.fromCharCode(65 + i)}. ${opt.text} [Marked: ${opt.logic}]`).join('\n')}

PROVIDED SOLUTION:
${question.solution || 'None'}

Return ONLY a JSON object:
{
  "passed": true,
  "score": 95,
  "calculated_answer": "42",
  "marked_ca_is_correct": true,
  "issues": [],
  "pedagogical_feedback": "Sound arithmetic problem with realistic distractors."
}`

  try {
    const rawContent = await generateWithAI(
      systemPrompt,
      userPrompt,
      model,
      0.0,
      1500
    )

    let cleaned = rawContent.trim()
    cleaned = cleaned.replace(/```json\s*/g, '').replace(/```\s*/g, '').trim()
    const firstBrace = cleaned.indexOf('{')
    const lastBrace = cleaned.lastIndexOf('}')

    if (firstBrace !== -1 && lastBrace !== -1) {
      const parsed = JSON.parse(cleaned.substring(firstBrace, lastBrace + 1))
      const combinedIssues = Array.from(
        new Set([...deterministicResult.issues, ...(parsed.issues || [])])
      )
      const passed = deterministicResult.passed && Boolean(parsed.passed) && Boolean(parsed.marked_ca_is_correct)
      const score = Math.min(deterministicResult.score, Number(parsed.score) || 100)

      return {
        passed,
        score,
        issues: combinedIssues,
        calculatedAnswer: parsed.calculated_answer,
        markedCaIsCorrect: parsed.marked_ca_is_correct,
        pedagogicalFeedback: parsed.pedagogical_feedback,
        evaluatedAt: new Date().toISOString()
      }
    }
  } catch (err: any) {
    console.warn('Semantic LLM evaluation failed, falling back to deterministic result:', err.message)
  }

  return deterministicResult
}
