import { NextRequest, NextResponse } from 'next/server'
import { generateWithAI } from '@/lib/ai-client'

export async function POST(request: NextRequest) {
  try {
    const data = await request.json()
    
    // Validate required fields
    const requiredFields = ['question', 'options', 'model']
    for (const field of requiredFields) {
      if (!data[field]) {
        return NextResponse.json(
          { error: `Missing required field: ${field}` },
          { status: 400 }
        )
      }
    }
    
    const question = data.question
    const options = data.options || []
    const solution = data.solution || ''
    const image = data.image || ''
    const model = data.model || 'gpt-4o'
    const questionType = data.questionType || 'mathematical'
    
    // Build verification prompt
    const verifyPrompt = `You are an expert mathematical question verifier with deep expertise in mathematical correctness, problem-solving, and educational content validation. Your task is to meticulously verify a mathematical question and its options for absolute correctness.

⚠️⚠️⚠️ CRITICAL: YOU MUST SOLVE THE QUESTION COMPLETELY BEFORE VERIFYING ANYTHING ⚠️⚠️⚠️

QUESTION TO VERIFY:
${question}

${solution ? `PROVIDED SOLUTION:\n${solution}\n` : ''}

OPTIONS PROVIDED:
${options.map((opt: any, idx: number) => 
  `${String.fromCharCode(65 + idx)}. ${opt.text} ${opt.logic === 'CA' ? '(MARKED AS CORRECT ANSWER)' : `(Logic: ${opt.logic})`}`
).join('\n')}

${image ? `IMAGE DESCRIPTION:\n${image}\n` : ''}

MANDATORY VERIFICATION PROCESS (FOLLOW THESE STEPS IN ORDER):

STEP 1: UNDERSTAND THE QUESTION
- Read the question carefully and identify what is being asked
- Identify all given information, constraints, and conditions
- Determine what type of mathematical problem this is
- Check if the question is well-formed and unambiguous

STEP 2: SOLVE THE QUESTION COMPLETELY
- Solve the problem step-by-step from scratch
- Show ALL your work mentally (you don't need to write it, but think through it)
- Calculate the final answer carefully
- Verify your answer by plugging it back into the problem
- Check that your answer satisfies ALL conditions in the question
- Ensure your answer is in the correct format (fraction, decimal, whole number, etc.)

STEP 3: VERIFY THE MARKED CORRECT ANSWER
- Check which option is currently marked as "CA" (Correct Answer)
- Compare the marked CA option with your calculated answer
- If they match exactly (or are mathematically equivalent), the CA is correct
- If they don't match, the CA is WRONG and you must identify the correct option

STEP 4: VERIFY ALL OPTIONS INDIVIDUALLY
- For EACH option, check if it could be the correct answer:
  - Option A: Is this the correct answer? (Yes/No)
  - Option B: Is this the correct answer? (Yes/No)
  - Option C: Is this the correct answer? (Yes/No)
  - Option D: Is this the correct answer? (Yes/No)
  - (Continue for all options)
- Exactly ONE option should be correct
- ALL other options should be incorrect

STEP 5: VERIFY DISTRACTOR LOGIC AND OPTION VALUES
- For each incorrect option, check if the provided logic accurately describes why it's wrong
- IMPORTANT: Only flag option value/logic mismatches if they are MATHEMATICALLY SIGNIFICANT
- Minor discrepancies or alternative valid interpretations should NOT be flagged as errors
- Only correct option values if:
  * The logic clearly describes a specific error (e.g., "Used subtraction instead") AND
  * The current option value is clearly wrong (e.g., logic says "subtraction" but value is the addition result)
  * The mismatch would confuse students or make the question invalid
- If the logic is reasonable and the option is clearly incorrect (even if not perfectly matching the logic description), do NOT change it
- Be conservative: Only change things when there are clear mathematical errors, not stylistic differences

STEP 6: VERIFY THE QUESTION ITSELF
- Check if the question has any mathematical errors
- Check if the question is solvable with the given information
- Check if there are any contradictions in the question
- Check if the question is unambiguous

STEP 7: VERIFY THE SOLUTION (if provided)
- Check if the provided solution correctly solves the problem
- Verify that the solution leads to the correct answer
- Check if the solution matches the correct option

STEP 8: VERIFY CONTEXT PRACTICALITY AND REASONABLENESS (FOR WORD PROBLEMS AND IMAGE-BASED QUESTIONS WITH CONTEXT)
${questionType === 'word-problems' || questionType === 'image-based' ? `- Check if the context/scenario is practical and reasonable:
  * Are the quantities realistic? (e.g., prices, speeds, ages, amounts, distances, time)
  * Are the timeframes logical? (e.g., can someone really do X in Y time?)
  * Are the ages appropriate for the activities described?
  * Are the scenarios believable and possible in real life?
  * Are units and measurements consistent and realistic?
  * Are the numbers appropriate for the grade level?
- Check for impractical scenarios:
  * ❌ "A student solving 200 problems in 5 minutes" (impossible - too fast)
  * ❌ "A 5-year-old driving a car" (age-inappropriate)
  * ❌ "Buying a house for $5" (unrealistic price - too low)
  * ❌ "Running 1000 miles per hour" (impossible speed)
  * ❌ "A person who is 200 years old" (unrealistic age)
  * ❌ "A 3rd grader solving calculus problems" (grade-inappropriate)
  * ❌ "Walking 500 miles in 1 hour" (impossible distance/time)
  * ❌ "A book costing $0.01" (unrealistic price for most books)
- Check for reasonable scenarios:
  * ✅ "A student solving 10 problems in 30 minutes" (reasonable pace)
  * ✅ "A 16-year-old learning to drive" (age-appropriate)
  * ✅ "Buying a book for $15" (realistic price)
  * ✅ "Running 6 miles per hour" (reasonable speed)
  * ✅ "A person who is 35 years old" (realistic age)
  * ✅ "A 5th grader solving multiplication problems" (grade-appropriate)
  * ✅ "Walking 3 miles in 1 hour" (reasonable distance/time)
  * ✅ "A toy costing $12.99" (realistic price)
- If context is impractical or unreasonable:
  * Set hasErrors: true
  * Add error: "Context is impractical/unreasonable: [description of specific issue]"
  * Add to contextIssues array: [detailed list of all context problems found]
  * Set contextCorrected: true
  * Provide corrected question with practical and reasonable context
  * Maintain the same mathematical structure and difficulty
  * Only change the context/scenario values, not the math problem itself
  * Ensure corrected values are:
    - Realistic and believable
    - Age-appropriate for the grade level
    - Consistent with real-world expectations
    - Mathematically equivalent (same problem type, same operations)
- Examples of context corrections:
  * "200 problems in 5 minutes" → "20 problems in 30 minutes" (maintains same rate concept)
  * "$5 for a house" → "$150,000 for a house" (realistic price)
  * "200 years old" → "35 years old" (realistic age)
  * "1000 mph" → "60 mph" (reasonable speed)
  * "A 3rd grader doing calculus" → "A 3rd grader doing addition" (grade-appropriate)
  * "500 miles in 1 hour" → "3 miles in 1 hour" (reasonable walking speed)` : '- Context verification: N/A (mathematical question without context)'}

CRITICAL ERROR DETECTION RULES:
1. If the marked CA is WRONG:
   - Set hasErrors: true
   - Add error: "Incorrect answer marked as correct. The correct answer is [option letter]."
   - Mark the actual correct option as "CA"
   - Keep the wrong option but update its logic to explain why it's wrong

2. If a distractor is actually correct:
   - Set hasErrors: true
   - Add error: "Option [letter] is marked as incorrect but is actually correct."
   - Replace that distractor with a new incorrect option
   - Provide appropriate logic for the new distractor

3. If the question has mathematical errors:
   - Set hasErrors: true
   - Add error: "Question contains mathematical error: [description]"
   - Provide corrected question text

4. If the solution doesn't match the correct answer:
   - Set hasErrors: true
   - Add error: "Solution does not match the correct answer."
   - Provide corrected solution

5. If distractor logic is inaccurate:
   - Set hasErrors: true
   - Add error: "Distractor logic for option [letter] is inaccurate."
   - Provide corrected logic
   - Ensure the option value matches the corrected logic

6. If an option value does not match its logic (ONLY FLAG IF MATHEMATICALLY SIGNIFICANT):
   - Only flag this if the mismatch is clear and would make the question confusing or invalid
   - Be conservative: If the option is clearly incorrect (even if not perfectly matching the logic), that's acceptable
   - Only set hasErrors: true if:
     * The logic describes a specific error AND
     * The current option value is clearly the correct answer (not just a different wrong answer)
     * The mismatch would make the question mathematically invalid
   - Examples of when to flag:
     * Logic: "Used subtraction instead" but option value is the correct answer → FLAG
     * Logic: "Used subtraction instead" but option value is a different wrong answer → DO NOT FLAG (acceptable)
     * Logic: "Calculation error" but option is clearly wrong → DO NOT FLAG (acceptable, even if not specific)
   - Only update option values if the current value is mathematically wrong in a way that contradicts the logic

7. If the context is impractical or unreasonable:
   - Set hasErrors: true
   - Set contextCorrected: true
   - Add error: "Context is impractical/unreasonable: [specific issue, e.g., 'Student solving 200 problems in 5 minutes is impossible']"
   - Add to contextIssues array: [detailed list of all context problems, e.g., "Quantity too high: 200 problems", "Time too short: 5 minutes", "Rate is unrealistic: 40 problems per minute"]
   - Provide corrected question with practical context
   - Ensure the corrected context:
     * Maintains the same mathematical problem structure
     * Uses realistic quantities, timeframes, and scenarios
     * Is age-appropriate for the grade level (if grade level can be inferred)
     * Is believable and possible in real life
     * Preserves the mathematical relationships (e.g., if original was about rate, corrected should also be about rate)
   - Example corrections:
     * "200 problems in 5 minutes" → "20 problems in 30 minutes" (maintains rate concept, more realistic)
     * "$5 for a house" → "$150,000 for a house" (realistic price)
     * "200 years old" → "35 years old" (realistic age)
     * "1000 mph" → "60 mph" (reasonable speed)
     * "A 3rd grader solving calculus" → "A 3rd grader solving addition" (grade-appropriate)
     * "500 miles in 1 hour" → "3 miles in 1 hour" (reasonable walking speed)
   - CRITICAL: Only change context values, NOT the mathematical structure or operations
   - CRITICAL: The corrected question should solve to the same type of answer (same units, same format)

OUTPUT FORMAT (JSON only, no markdown):
{
  "hasErrors": true/false,
  "errors": ["detailed list of all errors found"],
  "correctedQuestion": "corrected question text (only if question had errors, otherwise same as input)",
  "correctedOptions": [
    {"text": "option text", "logic": "CA" or "error description"},
    ...
  ],
  "correctedSolution": "corrected solution (only if solution had errors, otherwise same as input)",
  "contextCorrected": true/false,
  "contextIssues": ["list of context issues found, e.g., 'Quantity too high: 200 problems', 'Time too short: 5 minutes'"],
  "verificationNotes": "detailed explanation of verification process, what was checked, and any corrections made"
}

CRITICAL OUTPUT REQUIREMENTS:
- BE CONSERVATIVE: Only flag errors if there are ACTUAL mathematical mistakes or clear context issues, not minor discrepancies
- If the question is mathematically correct, context is reasonable, and the correct answer is properly marked: set "hasErrors": false
- If no errors are found: set "hasErrors": false and return original question/options/solution EXACTLY as provided (unchanged)
- Only set "hasErrors": true if there are clear mathematical errors or impractical context that need correction
- DO NOT change correct answers, solutions, or options just because they could be worded differently
- DO NOT change option values unless they are mathematically wrong (e.g., a distractor is actually correct)
- The "correctedOptions" array MUST have EXACTLY ${options.length} options (same as input) - DO NOT add or remove options
- Exactly ONE option MUST have "logic": "CA"
- If context was corrected: set "contextCorrected": true and populate "contextIssues" with detailed list of problems found
- If context was NOT corrected: set "contextCorrected": false and "contextIssues": []
- "verificationNotes" MUST include: "I solved the question and got [your answer]. The correct option is [letter]." If context was corrected, also mention: "Context was corrected for practicality: [brief summary]."
- Return ONLY valid JSON, no markdown code blocks, no explanations outside JSON
- Be extremely careful and thorough - mathematical accuracy and context reasonableness are both critical
- CRITICAL: Maintain the exact same number of options - if you need to fix an option, replace it in place, do not add or remove options
- CONSERVATIVE APPROACH: When in doubt about mathematical correctness, do NOT change anything - only correct clear mathematical errors
- CONTEXT CORRECTION: Only correct context if it is clearly impractical or unreasonable - be conservative but thorough`

    try {
      const systemPrompt = `You are an expert mathematical question verifier with exceptional attention to detail. Your primary responsibility is to ensure absolute mathematical correctness. 

CRITICAL INSTRUCTIONS:
1. You MUST solve every question completely from scratch before verifying anything
2. You MUST verify each option individually to ensure only one is correct
3. You MUST check that the marked correct answer is actually correct
4. You MUST verify that all distractors are actually incorrect
5. Mathematical accuracy is paramount - be extremely thorough
6. Always return valid JSON only, no markdown code blocks`

      const content = await generateWithAI(
        systemPrompt,
        verifyPrompt,
        model,
        0.0,
        3000
      )
      
      // Parse JSON from response
      let cleanedContent = content.trim()
      cleanedContent = cleanedContent.replace(/```json\s*/g, '')
      cleanedContent = cleanedContent.replace(/```\s*/g, '')
      cleanedContent = cleanedContent.trim()
      
      // Extract JSON object
      const firstBrace = cleanedContent.indexOf('{')
      const lastBrace = cleanedContent.lastIndexOf('}')
      
      if (firstBrace === -1 || lastBrace === -1 || lastBrace <= firstBrace) {
        console.error('Failed to find JSON object. Content preview:', cleanedContent.substring(0, 500))
        throw new Error('Failed to find JSON object in response.')
      }
      
      const jsonContent = cleanedContent.substring(firstBrace, lastBrace + 1)
      let parsed
      try {
        parsed = JSON.parse(jsonContent)
      } catch (parseError: any) {
        console.error('JSON parse error:', parseError.message)
        console.error('JSON content preview:', jsonContent.substring(0, 500))
        throw new Error(`Failed to parse JSON response: ${parseError.message}`)
      }
      
      // Validate that corrected options have the same number as input
      if (parsed.correctedOptions && Array.isArray(parsed.correctedOptions)) {
        if (parsed.correctedOptions.length !== options.length) {
          console.warn(`Corrected options count (${parsed.correctedOptions.length}) doesn't match input (${options.length}). Adjusting...`)
          // If too many options, trim to original count
          if (parsed.correctedOptions.length > options.length) {
            parsed.correctedOptions = parsed.correctedOptions.slice(0, options.length)
          }
          // If too few options, pad with original options
          else if (parsed.correctedOptions.length < options.length) {
            const originalOptions = [...options]
            const correctedOptions = [...parsed.correctedOptions]
            // Keep corrected options and fill remaining with original
            while (correctedOptions.length < options.length) {
              const originalIndex = correctedOptions.length
              correctedOptions.push({
                text: originalOptions[originalIndex].text,
                logic: originalOptions[originalIndex].logic
              })
            }
            parsed.correctedOptions = correctedOptions
          }
        }
      }
      
      return NextResponse.json({ 
        verified: true,
        result: parsed
      })
    } catch (error: any) {
      // If model is not available, fallback
      if (error?.message?.includes('model') || error?.code === 'model_not_found') {
        const fallbackModel = model.startsWith('agnes-') ? 'agnes-3-flash' : 'gpt-4o'
        console.warn(`${model} not available for verification, falling back to ${fallbackModel}`)
        const systemPrompt = `You are an expert mathematical question verifier with exceptional attention to detail. Your primary responsibility is to ensure absolute mathematical correctness. 

CRITICAL INSTRUCTIONS:
1. You MUST solve every question completely from scratch before verifying anything
2. You MUST verify each option individually to ensure only one is correct
3. You MUST check that the marked correct answer is actually correct
4. You MUST verify that all distractors are actually incorrect
5. Mathematical accuracy is paramount - be extremely thorough
6. Always return valid JSON only, no markdown code blocks`

        const content = await generateWithAI(
          systemPrompt,
          verifyPrompt,
          fallbackModel,
          0.0,
          3000
        )
        
        let cleanedContent = content.trim()
        cleanedContent = cleanedContent.replace(/```json\s*/g, '')
        cleanedContent = cleanedContent.replace(/```\s*/g, '')
        cleanedContent = cleanedContent.trim()
        
        const firstBrace = cleanedContent.indexOf('{')
        const lastBrace = cleanedContent.lastIndexOf('}')
        
        if (firstBrace === -1 || lastBrace === -1 || lastBrace <= firstBrace) {
          console.error('Failed to find JSON object. Content preview:', cleanedContent.substring(0, 500))
          throw new Error('Failed to find JSON object in response.')
        }
        
        const jsonContent = cleanedContent.substring(firstBrace, lastBrace + 1)
        let parsed
        try {
          parsed = JSON.parse(jsonContent)
        } catch (parseError: any) {
          console.error('JSON parse error:', parseError.message)
          console.error('JSON content preview:', jsonContent.substring(0, 500))
          throw new Error(`Failed to parse JSON response: ${parseError.message}`)
        }
        
        // Validate that corrected options have the same number as input
        if (parsed.correctedOptions && Array.isArray(parsed.correctedOptions)) {
          if (parsed.correctedOptions.length !== options.length) {
            console.warn(`Corrected options count (${parsed.correctedOptions.length}) doesn't match input (${options.length}). Adjusting...`)
            // If too many options, trim to original count
            if (parsed.correctedOptions.length > options.length) {
              parsed.correctedOptions = parsed.correctedOptions.slice(0, options.length)
            }
            // If too few options, pad with original options
            else if (parsed.correctedOptions.length < options.length) {
              const originalOptions = [...options]
              const correctedOptions = [...parsed.correctedOptions]
              // Keep corrected options and fill remaining with original
              while (correctedOptions.length < options.length) {
                const originalIndex = correctedOptions.length
                correctedOptions.push({
                  text: originalOptions[originalIndex].text,
                  logic: originalOptions[originalIndex].logic
                })
              }
              parsed.correctedOptions = correctedOptions
            }
          }
        }
        
        return NextResponse.json({ 
          verified: true,
          result: parsed
        })
      } else {
        throw error
      }
    }
  } catch (error: any) {
    console.error('Error verifying question:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to verify question' },
      { status: 500 }
    )
  }
}

