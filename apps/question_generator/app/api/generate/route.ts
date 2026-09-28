import { NextRequest, NextResponse } from 'next/server'
import { getOpenAIClient } from '@/lib/openai'
import { analyzeImageForQuestion, generateWithAI, getAIProvider } from '@/lib/ai-client'
import { doesNaraModelSupportVision } from '@/lib/nararouter'
import { evaluateDeterministic } from '@/lib/eval-layer'
import { loadCurriculumSubskills } from '@/lib/curriculum'
import { parseNumberOfOptions, determineQuestionType } from '@/lib/question-utils'

export async function POST(request: NextRequest) {
  try {
    const data = await request.json()
    
    // Validate required fields
    const requiredFields = ['baseQuestion', 'numCopyQuestions', 'model']
    for (const field of requiredFields) {
      if (!data[field]) {
        return NextResponse.json(
          { error: `Missing required field: ${field}` },
          { status: 400 }
        )
      }
    }
    
    // Parse number of options
    const baseQuestion = data.baseQuestion || ''
    const numOptions = data.numOptions 
      ? parseInt(data.numOptions, 10)
      : parseNumberOfOptions(baseQuestion)
    
    const difficulty = data.difficulty || 'Medium'
    const grade = data.grade || ''
    const curriculum = data.curriculum || ''
    const notes = (data.notes || '').trim() // Ensure empty string if only whitespace
    const solution = data.solution || ''
    const images = data.images || ''
    const imageFiles = data.imageFiles || [] // Array of base64 encoded images
    const numQuestions = parseInt(data.numCopyQuestions, 10)
    const model = data.model || 'gpt-4o'
    const questionTypeFromUrl = data.questionType || null
    // Determine question type
    let questionType: 'mathematical' | 'word_problem' | 'image_based'
    if (questionTypeFromUrl) {
      if (questionTypeFromUrl === 'word-problems') {
        questionType = 'word_problem'
      } else if (questionTypeFromUrl === 'mathematical') {
        questionType = 'mathematical'
      } else if (questionTypeFromUrl === 'image-based') {
        questionType = 'image_based'
      } else {
        questionType = determineQuestionType(baseQuestion, notes)
      }
    } else {
      questionType = determineQuestionType(baseQuestion, notes)
    }

    // Pre-analyze images once if image-based and images are provided
    let preAnalyzedImageContent = ''
    if (questionType === 'image_based' && imageFiles.length > 0) {
      try {
        console.log(`Analyzing ${imageFiles.length} uploaded image(s) once for parallel generation...`)
        const provider = getAIProvider(model)
        let visionModel = model
        if (provider === 'openai') {
          visionModel = model === 'gpt-4o' || model === 'gpt-4-turbo' ? model : 'gpt-4o'
        } else if (provider === 'nararouter') {
          visionModel = doesNaraModelSupportVision(model) ? model : 'agnes-3-flash'
        } else {
          visionModel = model.startsWith('gemini-') ? model : 'gemini-1.5-pro'
        }

        const analyses = await Promise.all(
          imageFiles.map((img: string) => analyzeImageForQuestion(img, visionModel))
        )
        preAnalyzedImageContent = analyses
          .map((analysis, index) => `Image ${index + 1} Analysis:\n${analysis}`)
          .join('\n\n---\n\n')
        console.log('Image pre-analysis completed successfully')
      } catch (err: any) {
        console.error('Error pre-analyzing images:', err)
        preAnalyzedImageContent = `[Image analysis failed: ${err.message}. Using images as reference only.]`
      }
    }

    // Calculate parallel batches (max 2-3 questions per batch for optimal speed & reliability)
    const batches = calculateBatches(numQuestions)
    console.log(`Parallel generation: Generating ${numQuestions} question(s) in ${batches.length} parallel batch(es):`, batches)

    const batchPromises = batches.map((batchCount, index) =>
      generateQuestionsWithGPT(
        baseQuestion,
        notes,
        solution,
        images,
        imageFiles,
        numOptions,
        batchCount,
        difficulty,
        grade,
        curriculum,
        model,
        questionTypeFromUrl,
        preAnalyzedImageContent,
        index,
        batches.length
      )
    )

    const batchResults = await Promise.all(batchPromises)
    const questions = batchResults.flat().slice(0, numQuestions)

    // Run Eval Layer (Tier 1 Deterministic Validation) on all generated questions
    const evaluatedQuestions = questions.map((q) => {
      const evalStatus = evaluateDeterministic(q, numOptions, notes)
      return {
        ...q,
        evalStatus
      }
    })

    return NextResponse.json({ questions: evaluatedQuestions })
  } catch (error: any) {
    console.error('Error generating questions:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to generate questions' },
      { status: 500 }
    )
  }
}

// Partition requested questions into optimal parallel batches (max 2-3 per batch)
function calculateBatches(numQuestions: number): number[] {
  if (numQuestions <= 2) return [numQuestions]
  if (numQuestions === 3) return [2, 1]
  if (numQuestions === 4) return [2, 2]
  if (numQuestions === 5) return [3, 2]
  if (numQuestions === 6) return [2, 2, 2]
  if (numQuestions === 7) return [3, 2, 2]
  if (numQuestions === 8) return [3, 3, 2]
  const batches: number[] = []
  let remaining = numQuestions
  while (remaining > 0) {
    const size = remaining >= 6 ? 3 : (remaining >= 4 ? 2 : remaining)
    batches.push(size)
    remaining -= size
  }
  return batches
}

async function generateQuestionsWithGPT(
  baseQuestion: string,
  notes: string,
  solution: string,
  images: string,
  imageFiles: any[],
  numOptions: number,
  numQuestions: number,
  difficulty: string,
  grade: string,
  curriculum: string,
  model: string,
  questionTypeFromUrl: string | null,
  preAnalyzedImageContent: string = '',
  batchIndex: number = 0,
  totalBatches: number = 1
) {
  // Load relevant subskills
  let subskillsText = 'General math concepts'
  if (grade && curriculum) {
    const subskills = loadCurriculumSubskills(grade, curriculum)
    subskillsText = subskills.slice(0, 4).join(', ') || 'General math concepts'
  }
  
  // Determine question type
  let questionType: 'mathematical' | 'word_problem' | 'image_based'
  if (questionTypeFromUrl) {
    if (questionTypeFromUrl === 'word-problems') {
      questionType = 'word_problem'
    } else if (questionTypeFromUrl === 'mathematical') {
      questionType = 'mathematical'
    } else if (questionTypeFromUrl === 'image-based') {
      questionType = 'image_based'
    } else {
      questionType = determineQuestionType(baseQuestion, notes)
    }
  } else {
    questionType = determineQuestionType(baseQuestion, notes)
  }
  
  // Analyze uploaded images if present and for image-based questions
  let analyzedImageContent = preAnalyzedImageContent
  if (!analyzedImageContent && questionType === 'image_based' && imageFiles.length > 0) {
    try {
      console.log(`Analyzing ${imageFiles.length} uploaded image(s) for content extraction...`)
      // Use a vision-capable model for analysis
      const provider = getAIProvider(model)
      let visionModel = model
      if (provider === 'openai') {
        visionModel = model === 'gpt-4o' || model === 'gpt-4-turbo' ? model : 'gpt-4o'
      } else if (provider === 'nararouter') {
        visionModel = doesNaraModelSupportVision(model) ? model : 'agnes-3-flash'
      } else {
        // Gemini - use the model if it supports vision, otherwise use gemini-1.5-pro
        visionModel = model.startsWith('gemini-') ? model : 'gemini-1.5-pro'
      }
      
      // Analyze all uploaded images
      const analysisPromises = imageFiles.map((img: string, index: number) => {
        console.log(`Analyzing image ${index + 1} of ${imageFiles.length}...`)
        return analyzeImageForQuestion(img, visionModel)
      })
      const analyses = await Promise.all(analysisPromises)
      analyzedImageContent = analyses
        .map((analysis, index) => `Image ${index + 1} Analysis:\n${analysis}`)
        .join('\n\n---\n\n')
      
      console.log('Image analysis completed successfully')
    } catch (error: any) {
      console.error('Error analyzing images:', error)
      // Continue without analysis if it fails, but log the error
      analyzedImageContent = `[Image analysis failed: ${error.message}. Using images as reference only.]`
    }
  }
  
  // Build system prompt - TIER 1: Universal System Requirements
  const systemPrompt = `You are an expert educational content generator specializing in creating high-quality mathematical questions aligned with US curricula standards. Your primary task is to generate pedagogically sound multiple-choice questions that test specific mathematical skills and concepts while maintaining strict adherence to provided guidelines and formats.

You will follow a three-tier hierarchical approach when generating questions:

TIER 1: Universal System Requirements (Always Apply)
These rules apply to ALL questions regardless of type.

1.1 Format Preservation (CRITICAL)
- Preserve EXACT format and structure of the base question
- Maintain SAME question type and presentation style
- Match punctuation, capitalization, and formatting exactly
- Replicate any special formatting (bold, italics, mathematical notation)

1.2 Mathematical Correctness (CRITICAL)
- All questions must be mathematically accurate
- Verify calculations before finalizing
- Ensure solutions exist and are mathematically valid
- Check that all conditions are consistent with no contradictions

1.3 Answer Accuracy (CRITICAL - MUST VERIFY)
- CRITICAL: You MUST solve each question completely before marking any option as correct
- The correct answer must be verified by solving the problem step-by-step
- Work backward from the answer to confirm it satisfies all conditions
- Double-check all calculations to avoid errors
- DO NOT mark an option as "CA" (Correct Answer) unless you have verified it is mathematically correct
- If you are unsure, solve the problem completely first, then mark the verified correct answer
- Incorrect answers marked as CA will cause significant errors

1.4 Number of Options (CRITICAL - EXACT MATCH REQUIRED)
- CRITICAL: You MUST match the EXACT number of options from the base question
- If base has 4 options, you MUST generate EXACTLY 4 options - NO MORE, NO LESS
- If base has 3 options, you MUST generate EXACTLY 3 options - NO MORE, NO LESS
- If base has 2 options, you MUST generate EXACTLY 2 options - NO MORE, NO LESS
- Count the options in the base question carefully before generating
- The number of options is specified as ${numOptions} - you MUST generate EXACTLY ${numOptions} options per question
- DO NOT add extra options or remove options - the count must match exactly

1.5 Distractor Generation Strategy
You must create distractors (incorrect options) using a varied mix of the following approaches:
A. Base Question Options (when applicable) - Adapt distractor logic from the base question's options
B. Common Student Errors - Include options that reflect typical mistakes students make (sign errors, order of operations mistakes, formula misapplication)
C. Plausible Distractors - Calculation errors (one step wrong, but logical), numbers that appear in the problem but aren't the answer, results from incorrect methods that seem reasonable

CRITICAL: Options must NOT follow a predictable pattern. Mix different distractor types across your generated questions.

1.6 Auto-Check Requirement
Before providing your final answer, you must:
- Solve each question completely
- Verify the correct answer
- Check that distractors are plausible but incorrect
- Confirm all formatting matches the base question
- CRITICAL: Verify that you have generated EXACTLY ${numOptions} options (count them!)
- CRITICAL: Verify that all SME notes (if provided) have been followed precisely

1.7 SME Notes Compliance (CRITICAL - HIGHEST PRIORITY)
- SME notes are provided by Subject Matter Experts and contain specific requirements
- CRITICAL: SME notes have HIGHEST PRIORITY - they override and supplement all other instructions
- CRITICAL: You MUST follow ALL instructions in SME notes precisely and completely
- If SME notes specify certain constraints, formats, or requirements, you MUST adhere to them
- If SME notes specify certain answer types, number ranges, or formats, you MUST use them
- If SME notes specify certain scenarios or contexts, you MUST incorporate them
- DO NOT ignore or skip any part of the SME notes
- SME notes are MANDATORY - treat them as non-negotiable requirements

1.8 Anti-Hallucination Requirements (CRITICAL - NO FABRICATION)
- CRITICAL: You MUST base ALL content ONLY on the provided base question, SME notes, and explicit instructions
- DO NOT invent, fabricate, or add information that is NOT present in the base question or SME notes
- DO NOT add extra details, facts, or context that were not in the original base question
- DO NOT create scenarios, characters, or situations that deviate from what's provided
- DO NOT invent mathematical concepts, formulas, or methods not present in the base question
- DO NOT add unnecessary complexity or additional constraints not in the original
- DO NOT make up numbers, values, or quantities that aren't derived from the base question
- DO NOT add cultural references, names, or details not present in the base question
- DO NOT create solutions or methods that weren't implied by the base question structure
- CRITICAL: If information is not explicitly provided, DO NOT assume or invent it
- CRITICAL: Every element in your generated question must trace back to the base question or SME notes
- When varying content, ONLY change what is explicitly allowed (numbers, names, contexts) while maintaining structure
- If unsure whether to include something, ask: "Was this in the base question or SME notes?" If NO, exclude it
- Verify: Every sentence, number, and concept in your generated question has a clear source in the provided materials
- DO NOT hallucinate: If you don't see it in the base question or SME notes, it doesn't exist - don't create it`
  
  // Build user prompt
  const solutionText = solution ? `\nBase Solution: ${solution}` : ''
  const imageInfo = images ? `\nBase Question Image Description: ${images}` : ''
  const uploadedImageInfo = imageFiles.length > 0 
    ? analyzedImageContent
      ? `\n${'='.repeat(80)}
UPLOADED IMAGES ANALYSIS (CRITICAL - USE THIS CONTENT):
${'='.repeat(80)}
${analyzedImageContent}
${'='.repeat(80)}

CRITICAL INSTRUCTIONS FOR USING IMAGE ANALYSIS:
- The above analysis contains ALL text, numbers, measurements, shapes, and visual elements extracted from the uploaded images
- You MUST use this analyzed content to generate questions that match the structure and content of the uploaded images
- All measurements, angles, side lengths, coordinates, and values in your generated questions should be based on or variations of the values found in the analysis
- Maintain the same image type (triangle → triangle, graph → graph, table → table) as shown in the analysis
- Use the same question format and structure as indicated by the analyzed content
- DO NOT invent new visual elements that were not present in the uploaded images
- The image analysis is the PRIMARY source of information for generating image-based questions
${'='.repeat(80)}`
      : `\nUPLOADED IMAGES: ${imageFiles.length} image(s) have been uploaded. These images are provided as base64 data and should be used as reference for generating similar visual elements.`
    : ''
  
  let userPrompt = ''
  
  if (questionType === 'mathematical') {
    userPrompt = `${'='.repeat(80)}
⚠️⚠️⚠️ CRITICAL: YOU MUST GENERATE EXACTLY ${numQuestions} QUESTIONS - NO MORE, NO LESS ⚠️⚠️⚠️
CRITICAL: The response MUST contain EXACTLY ${numQuestions} question objects in the JSON array.
${totalBatches > 1 ? `CRITICAL VARIATION (Parallel Batch ${batchIndex + 1} of ${totalBatches}): Ensure all numbers, contexts, and scenarios in these ${numQuestions} question(s) are distinct and unique (Variant Set #${batchIndex + 1}).\n` : ''}
CRITICAL: If you generate fewer than ${numQuestions} questions, the request will fail.
CRITICAL: If you generate more than ${numQuestions} questions, only the first ${numQuestions} will be used.
CRITICAL: Count your questions before submitting - ensure the array has EXACTLY ${numQuestions} elements.
${'='.repeat(80)}

BASE QUESTION (STUDY THIS CAREFULLY - READ THE ENTIRE QUESTION):
${baseQuestion}

⚠️⚠️⚠️ CRITICAL: READ THE ENTIRE BASE QUESTION ABOVE ⚠️⚠️⚠️
- The base question may be long - you MUST read it completely from start to finish
- Do NOT skip any part of the base question
- Pay attention to ALL details, context, scenarios, and formatting
- The base question contains ALL the information you need to generate similar questions
- If the base question is a word problem with a story/context, you MUST preserve that format
- If the base question has multiple sentences or paragraphs, read ALL of them
- The entire base question is your template - use it completely

${'='.repeat(80)}
⚠️⚠️⚠️ ANTI-HALLUCINATION CHECKLIST ⚠️⚠️⚠️
${'='.repeat(80)}
Before generating each question, verify:
- Am I only using information from the BASE QUESTION provided above?
- Am I only using requirements from SME NOTES (if provided)?
- Have I avoided adding any details NOT present in the base question?
- Have I avoided inventing scenarios, characters, or contexts not in the base?
- Are all numbers and values derived from or variations of the base question?
- Have I avoided adding mathematical concepts not present in the base question?
- Have I avoided adding unnecessary complexity or constraints?
- Can I trace every element of my generated question back to the base question or SME notes?

CRITICAL RULE: If you cannot identify the source of an element in the base question or SME notes, DO NOT include it.
${'='.repeat(80)}

${notes && notes.length > 0 ? `\n${'='.repeat(80)}
⚠️⚠️⚠️ TIER 3: SME NOTES (HIGHEST PRIORITY - ABSOLUTE MANDATORY REQUIREMENTS) ⚠️⚠️⚠️
${'='.repeat(80)}
CRITICAL: The following SME notes are MANDATORY and have HIGHEST PRIORITY over all other instructions.
CRITICAL: You MUST follow EVERY requirement in these SME notes precisely and completely.
CRITICAL: SME notes override and supplement Tiers 1 and 2 - they are non-negotiable.
CRITICAL: If SME notes conflict with other instructions, SME notes take precedence.
CRITICAL: Read these notes carefully and ensure ALL requirements are met in EVERY generated question.

SME NOTES CONTENT:
${notes}

⚠️⚠️⚠️ VERIFICATION CHECKLIST FOR SME NOTES ⚠️⚠️⚠️
Before finalizing each question, verify:
- Have I read and understood ALL SME notes requirements?
- Have I incorporated ALL requirements from SME notes into this question?
- Does this question follow ALL constraints specified in SME notes?
- Does this question use ALL formats/types specified in SME notes?
- CRITICAL: If SME notes specify answer format (mixed number, improper fraction, simplified, whole number, etc.), does the CORRECT ANSWER match that format exactly?
- CRITICAL: Have I verified that the answer marked as "CA" (Correct Answer) is in the format specified in SME notes?
- If SME notes specify answer types/ranges/formats, does this question use them?
- If SME notes specify scenarios/contexts, does this question incorporate them?
- Have I followed EVERY instruction in the SME notes, not just some of them?
- CRITICAL: Before marking any option as "CA", have I checked that it matches ALL SME notes format requirements?

SPECIFIC EXAMPLES OF SME NOTES FORMAT REQUIREMENTS:
- If SME notes say "answer should be a mixed number": The correct answer MUST be like "2 1/3" or "5 2/7", NOT "7/3" or "2.33"
- If SME notes say "answer should be simplified": The correct answer MUST be in simplest form (e.g., "3/4" not "6/8")
- If SME notes say "answer should be an improper fraction": The correct answer MUST be an improper fraction (e.g., "7/3" not "2 1/3")
- If SME notes specify any other format, the correct answer MUST follow it exactly

CRITICAL: These are the ONLY SME notes for this request. Do NOT use any notes from previous requests or conversations.
${'='.repeat(80)}\n` : '\nTIER 3: SME NOTES - None provided.\nCRITICAL: There are NO SME notes for this request. Do NOT use any notes from previous requests or conversations.\nProceed with Tiers 1 and 2 only. Ignore any notes that may have been mentioned in previous interactions.\n'}

${solution ? `Base Solution: ${solution}\n` : ''}${imageInfo ? `${imageInfo}\n` : ''}

TIER 2: Question-Specific Requirements - 2A: Mathematical Questions

Characteristics: Equations, expressions, calculations without real-world scenarios. No images/graphs.

Apply These Additional Requirements:

Mathematical Accuracy
- Verify all calculations are correct before finalizing
- Ensure solutions exist and are mathematically valid
- Check that all given conditions are consistent (no contradictions)

Problem Structure
- Clearly define what is given and what needs to be found
- Use proper mathematical notation and symbols
- Ensure the question is unambiguous
- Maintain logical flow from given information to the question

Answer Verification (CRITICAL)
- You MUST solve each question completely before generating options
- Work backward from the answer to verify it satisfies all conditions
- Check for extraneous solutions (e.g., square root problems, rational equations)
- CRITICAL: The answer format MUST match ALL requirements specified in SME notes
- If SME notes specify answer format (mixed number, improper fraction, simplified fraction, whole number, decimal, etc.), the correct answer MUST be in that exact format
- If SME notes say "answer should be a mixed number", the correct answer MUST be a mixed number (e.g., "2 1/3" not "7/3" or "2.33")
- If SME notes say "answer should be simplified", the correct answer MUST be in simplest form
- If SME notes specify any other format requirement, the correct answer MUST follow it exactly
- Verify units/dimensions if applicable
- CRITICAL: Only mark an option as "CA" if you have verified it is mathematically correct AND matches all SME notes format requirements
- Double-check your calculations - incorrect answers marked as CA will cause errors
- CRITICAL: Before finalizing the correct answer, verify it matches the format specified in SME notes

CRITICAL REQUIREMENTS FOR OPTIONS AND CORRECT ANSWERS:

1. OPTIONS FORMAT:
   - Each option MUST have a "text" field containing a COMPLETE, MEANINGFUL answer (e.g., "5/12", "0.42", "3/4", "2.5")
   - DO NOT use placeholder text like "Option A", "Option B", "Choice A", etc.
   - Each option MUST be a real, complete answer that a student could choose
   - Options should be in the same format as the base question's options (fractions, decimals, whole numbers, etc.)

2. CORRECT ANSWER (CRITICAL - MUST BE VERIFIED):
   - ONE and ONLY ONE option per question MUST have "logic": "CA" (Correct Answer)
   - CRITICAL: You MUST solve each question completely before marking the correct answer
   - The correct answer MUST be mathematically correct - verify by solving the problem step-by-step
   - Work backward from your answer to confirm it satisfies all conditions in the question
   - The correct answer MUST follow all SME notes requirements
   - Mark the correct answer clearly with "logic": "CA" - DO NOT mark incorrect answers as CA
   - If you are unsure which answer is correct, solve the problem completely first, then mark the verified correct answer
   
   VERIFICATION PROCESS (MANDATORY - FOLLOW THESE STEPS):
   Step 1: Read the question carefully and identify what is being asked
   Step 2: Solve the problem completely step-by-step (show your work mentally)
   Step 3: Calculate the final answer
   Step 4: Verify your answer by plugging it back into the problem or checking it
   Step 5: Check that your answer satisfies all conditions in the question
   Step 6: Only then, mark the option with your verified answer as "logic": "CA"
   Step 7: Generate distractors (incorrect options) with appropriate logic
   
   EXAMPLE OF CORRECT PROCESS:
   Question: "What is 15 + 27?"
   Step 1: Identify: Addition problem
   Step 2: Solve: 15 + 27 = 42
   Step 3: Verify: 42 - 15 = 27 ✓ (correct)
   Step 4: Mark option with "42" as "logic": "CA"
   Step 5: Generate distractors: "40" (logic: "Forgot to add ones"), "43" (logic: "Added incorrectly"), etc.
   
   ❌ WRONG: Marking "40" as CA because it's close to the answer
   ❌ WRONG: Marking the first option as CA without solving
   ❌ WRONG: Marking multiple options as CA
   ❌ WRONG: Guessing which answer is correct
   ✅ CORRECT: Solving completely, verifying, then marking only the verified correct answer as CA

3. INCORRECT OPTIONS (DISTRACTORS):
   - Each incorrect option MUST have a "logic" field explaining the error
   - Logic must be SHORT (3-6 words) describing the mistake
   - Distractors should be based on ACTUAL ERRORS students would make
   - Examples: "Added instead of multiplied", "Forgot to carry over", "Wrong denominator", "Calculation error"

4. OPTIONS COUNT:
   - Each question MUST have EXACTLY ${numOptions} options
   - All ${numOptions} options must be complete and valid answers

5. STEP-BY-STEP SOLUTIONS (CRITICAL - MUST BE COMPLETE AND DETAILED):
   - Each question MUST include a COMPLETE, DETAILED step-by-step solution in the "solution" field
   - CRITICAL: The solution MUST be complete in all sense - show ALL steps, calculations, and reasoning
   - ⚠️⚠️⚠️ CRITICAL FORMATTING REQUIREMENT ⚠️⚠️⚠️: Format each step on a NEW LINE using "Step 1:", "Step 2:", "Step 3:", etc.
   - ⚠️⚠️⚠️ YOU MUST USE \n (newline character) BETWEEN EACH STEP - DO NOT PUT MULTIPLE STEPS ON THE SAME LINE ⚠️⚠️⚠️
   - Each step MUST be clearly separated and on its own line for readability
   - Include ALL intermediate calculations and explanations
   - Show the complete work from start to finish - do NOT skip steps
   - Verify the final answer matches the correct option
   - Show the logical progression from the problem statement to the final answer with ALL steps
   - Make it educational and easy to follow - a student should be able to understand each step
   - Format: Use line breaks between steps (each step on a new line)
   ${solution ? '- Base the solution on the provided base solution, adapting steps to match each question\'s numbers/context' : ''}
   - Example format (CRITICAL: Each step MUST be on a separate line with \n):
     "Step 1: [First step explanation and calculation]\nStep 2: [Second step explanation and calculation]\nStep 3: [Final step and answer]"
   - CRITICAL: You MUST use \n (newline character) between each step - do NOT put multiple steps on the same line

QUALITY CHECKLIST (Self-Verify Before Finalizing):
✅ Format matches base question exactly
✅ Correct answer is mathematically verified
✅ CRITICAL: Correct answer format matches ALL SME notes requirements (if SME notes specify format)
✅ Options don't follow a predictable pattern
✅ CRITICAL: Number of options is EXACTLY ${numOptions} - count them to verify!
✅ CRITICAL: ALL SME notes (if provided) have been followed PRECISELY - verify each requirement, especially answer format requirements
✅ CRITICAL: Solution is COMPLETE with ALL steps shown - verify no steps are skipped
✅ CRITICAL: Solution is formatted with each step on a new line for readability
✅ No mathematical errors or logical contradictions

JSON FORMAT REQUIREMENTS:
- Your FIRST character MUST be [ (opening square bracket)
- Your LAST character MUST be ] (closing square bracket)
- Return ONLY a valid JSON array starting with [ and ending with ]
- NO markdown code blocks (no \`\`\`json or \`\`\`)
- NO explanations or text before or after the JSON
- Start response immediately with [
- End response with ]

EXAMPLE FORMAT:
[{"question": "...", "options": [{"text": "...", "logic": "CA"}, {"text": "...", "logic": "..."}, ...], "image": "", "solution": "Step 1: ...\nStep 2: ...\nStep 3: ..."}, ...]

CRITICAL FINAL REMINDER:
- You MUST return EXACTLY ${numQuestions} questions in the JSON array
- CRITICAL: Each question MUST have EXACTLY ${numOptions} options - NO MORE, NO LESS
- CRITICAL: Each solution MUST have steps on SEPARATE LINES using \n - do NOT put multiple steps on the same line
- CRITICAL: Solution format must be: "Step 1: ...\nStep 2: ...\nStep 3: ..." (with \n between each step)
- CRITICAL: Verify that sentence structure EXACTLY matches the base question (same grammatical patterns, word order, and sentence complexity)
- CRITICAL: Only change numbers, names, and context - DO NOT change sentence structure, grammatical patterns, or word order
- CRITICAL: Before marking any option as "CA", verify that the answer format matches ALL SME notes requirements
- CRITICAL: If SME notes specify answer format (mixed number, simplified fraction, etc.), the correct answer MUST be in that exact format
- Count your questions: The array must have exactly ${numQuestions} elements, no more, no less
- Count options in EACH question: Every question must have exactly ${numOptions} options
- Verify before submitting: Check that your JSON array contains exactly ${numQuestions} question objects
- Verify before submitting: Check that EACH question object has exactly ${numOptions} options in its options array
- Verify before submitting: Check that EACH solution has steps separated by \n (newline characters)
- Verify before submitting: Check that EACH question has the SAME sentence structure as the base question
- Verify before submitting: Check that EACH correct answer (marked with "CA") matches ALL SME notes format requirements
- DO NOT put multiple solution steps on the same line - each step MUST be on its own line with \n
- DO NOT change sentence structure, grammatical patterns, or word order - only change numbers, names, and context
- DO NOT ignore SME notes format requirements - if SME notes specify a format, the correct answer MUST match it
- ${notes && notes.length > 0 ? 'CRITICAL: Verify that ALL SME notes requirements have been followed in EVERY question, including answer format requirements' : ''}`
  } else {
    // Word Problems or Image-Based Questions
    const isImageBased = questionType === 'image_based'
    const questionTypeLabel = isImageBased ? 'Image-Based Questions' : 'Word Problems / Real-World Problems'
    const tier2Section = isImageBased ? '2C: Image-Based Questions' : '2B: Word Problems / Real-World Problems'
    
    userPrompt = `${'='.repeat(80)}
⚠️⚠️⚠️ CRITICAL: YOU MUST GENERATE EXACTLY ${numQuestions} QUESTIONS - NO MORE, NO LESS ⚠️⚠️⚠️
CRITICAL: The response MUST contain EXACTLY ${numQuestions} question objects in the JSON array.
${totalBatches > 1 ? `CRITICAL VARIATION (Parallel Batch ${batchIndex + 1} of ${totalBatches}): Ensure all numbers, contexts, and scenarios in these ${numQuestions} question(s) are distinct and unique (Variant Set #${batchIndex + 1}).\n` : ''}
CRITICAL: If you generate fewer than ${numQuestions} questions, the request will fail.
CRITICAL: If you generate more than ${numQuestions} questions, only the first ${numQuestions} will be used.
CRITICAL: Count your questions before submitting - ensure the array has EXACTLY ${numQuestions} elements.
${'='.repeat(80)}

BASE QUESTION (STUDY THIS CAREFULLY - READ THE ENTIRE QUESTION):
${baseQuestion}

⚠️⚠️⚠️ CRITICAL: READ THE ENTIRE BASE QUESTION ABOVE ⚠️⚠️⚠️
- The base question may be long - you MUST read it completely from start to finish
- Do NOT skip any part of the base question
- Pay attention to ALL details, context, scenarios, and formatting
- The base question contains ALL the information you need to generate similar questions
- If the base question is a word problem with a story/context, you MUST preserve that format
- If the base question has multiple sentences or paragraphs, read ALL of them
- The entire base question is your template - use it completely

${'='.repeat(80)}
⚠️⚠️⚠️ ANTI-HALLUCINATION CHECKLIST ⚠️⚠️⚠️
${'='.repeat(80)}
Before generating each question, verify:
- Am I only using information from the BASE QUESTION provided above?
- Am I only using requirements from SME NOTES (if provided)?
- Have I avoided adding any details NOT present in the base question?
- Have I avoided inventing scenarios, characters, or contexts not in the base?
- Are all numbers and values derived from or variations of the base question?
- Have I avoided adding mathematical concepts not present in the base question?
- Have I avoided adding unnecessary complexity or constraints?
- Can I trace every element of my generated question back to the base question or SME notes?

${isImageBased ? `CRITICAL FOR IMAGE-BASED QUESTIONS - ANTI-HALLUCINATION RULES:
- USE THE SAME IMAGE TYPE: If base question has a triangle, ALL generated questions must have triangles (not circles, rectangles, etc.)
- USE THE SAME IMAGE STRUCTURE: If base has a right triangle, generated questions should have right triangles (not equilateral, isosceles, etc. unless base specifies)
- MAINTAIN SAME VISUAL ELEMENTS: If base shows angles, all generated should show angles. If base shows sides, all should show sides.
- SAME QUESTION FORMAT: If base asks "What is the area?", generated should ask "What is the area?" (not "What is the perimeter?" or different question types)
- ONLY VARY NUMERICAL VALUES: Change the measurements (3 cm → 5 cm, 45° → 60°) but keep the same structure
- SAME MATHEMATICAL CONCEPT: If base is about area, all generated should be about area (not volume, perimeter, etc.)
- USE BASE IMAGE DESCRIPTION AS TEMPLATE: Follow the exact same format and structure as the base image description, only changing numbers
- DO NOT INVENT NEW VISUAL ELEMENTS: If base doesn't have a grid, don't add a grid. If base doesn't have labels, don't add labels.
- DO NOT CHANGE QUESTION TYPE: If base asks for a measurement, all should ask for measurements. If base asks for an angle, all should ask for angles.
- PRESERVE IMAGE DESCRIPTION FORMAT: Use the same sentence structure and detail level as the base image description

EXAMPLE:
Base: "A right triangle with base = 3 cm, height = 4 cm, hypotenuse = 5 cm. Question: What is the area?"
✅ CORRECT: "A right triangle with base = 5 cm, height = 6 cm, hypotenuse = 7.81 cm. Question: What is the area?"
❌ WRONG: "A circle with radius = 5 cm. Question: What is the circumference?" (different image type and question)
❌ WRONG: "A right triangle with base = 3 cm, height = 4 cm. Question: What is the perimeter?" (different question type)
❌ WRONG: "A right triangle with base = 3 cm, height = 4 cm, hypotenuse = 5 cm, and a grid showing coordinates. Question: What is the area?" (added grid not in base)` : ''}

CRITICAL RULE: If you cannot identify the source of an element in the base question or SME notes, DO NOT include it.
${'='.repeat(80)}

${notes && notes.length > 0 ? `\n${'='.repeat(80)}
⚠️⚠️⚠️ TIER 3: SME NOTES (HIGHEST PRIORITY - ABSOLUTE MANDATORY REQUIREMENTS) ⚠️⚠️⚠️
${'='.repeat(80)}
CRITICAL: The following SME notes are MANDATORY and have HIGHEST PRIORITY over all other instructions.
CRITICAL: You MUST follow EVERY requirement in these SME notes precisely and completely.
CRITICAL: SME notes override and supplement Tiers 1 and 2 - they are non-negotiable.
CRITICAL: If SME notes conflict with other instructions, SME notes take precedence.
CRITICAL: Read these notes carefully and ensure ALL requirements are met in EVERY generated question.

SME NOTES CONTENT:
${notes}

⚠️⚠️⚠️ VERIFICATION CHECKLIST FOR SME NOTES ⚠️⚠️⚠️
Before finalizing each question, verify:
- Have I read and understood ALL SME notes requirements?
- Have I incorporated ALL requirements from SME notes into this question?
- Does this question follow ALL constraints specified in SME notes?
- Does this question use ALL formats/types specified in SME notes?
- CRITICAL: If SME notes specify answer format (mixed number, improper fraction, simplified, whole number, etc.), does the CORRECT ANSWER match that format exactly?
- CRITICAL: Have I verified that the answer marked as "CA" (Correct Answer) is in the format specified in SME notes?
- If SME notes specify answer types/ranges/formats, does this question use them?
- If SME notes specify scenarios/contexts, does this question incorporate them?
- Have I followed EVERY instruction in the SME notes, not just some of them?
- CRITICAL: Before marking any option as "CA", have I checked that it matches ALL SME notes format requirements?
${isImageBased && ((notes && notes.toLowerCase().includes('table')) || (images && images.toLowerCase().includes('<table>')) || (baseQuestion && baseQuestion.toLowerCase().includes('table'))) ? `- CRITICAL: If SME notes specify table variation instructions, have I applied them to ALL table values in this question?
- CRITICAL: Are the table values in the specified range/format from SME notes (e.g., Easy: 1-20, Medium: 21-50, Hard: 51-100)?
- CRITICAL: Does this table have different values from the base question and all other generated questions?
- CRITICAL: If SME notes specify row count variations, does this table have the correct number of rows?
- CRITICAL: If SME notes specify value constraints (multiples, even numbers, etc.), do all table values meet those constraints?
- CRITICAL: If percentages are used in the table, do they sum to 100% as required?
- CRITICAL: Have I maintained the same table structure (columns, headers) as the base question unless SME notes specify otherwise?` : ''}
${isImageBased && ((notes && notes.toLowerCase().includes('chart')) || (images && (images.toLowerCase().includes('bar chart') || images.toLowerCase().includes('line graph') || images.toLowerCase().includes('dot plot') || images.toLowerCase().includes('scatter plot') || images.toLowerCase().includes('histogram')))) ? `- CRITICAL: Does this question's image description start with the SAME chart type as the base question?
- CRITICAL: If base question says "The image shows a line graph", does this copy also say "The image shows a line graph" (NOT "table" or other chart type)?
- CRITICAL: If base question says "The image shows a bar chart", does this copy also say "The image shows a bar chart" (NOT "table" or "line graph")?
- CRITICAL: Have I preserved the exact chart type from the base question?
- CRITICAL: Have I NOT converted a chart to a table?` : ''}

SPECIFIC EXAMPLES OF SME NOTES FORMAT REQUIREMENTS:
- If SME notes say "answer should be a mixed number": The correct answer MUST be like "2 1/3" or "5 2/7", NOT "7/3" or "2.33"
- If SME notes say "answer should be simplified": The correct answer MUST be in simplest form (e.g., "3/4" not "6/8")
- If SME notes say "answer should be an improper fraction": The correct answer MUST be an improper fraction (e.g., "7/3" not "2 1/3")
- If SME notes specify any other format, the correct answer MUST follow it exactly
${isImageBased && ((notes && notes.toLowerCase().includes('table')) || (images && images.toLowerCase().includes('<table>')) || (baseQuestion && baseQuestion.toLowerCase().includes('table'))) ? `- If SME notes specify table variations (e.g., "Easy: 1-20, Medium: 21-50, Hard: 51-100"), the table values MUST be within those ranges
- If SME notes specify "table values should be multiples of 5", ALL table values MUST be multiples of 5
- If SME notes specify row count (e.g., "Easy: 3 rows"), the table MUST have exactly that number of rows` : ''}

CRITICAL: These are the ONLY SME notes for this request. Do NOT use any notes from previous requests or conversations.
${'='.repeat(80)}\n` : '\nTIER 3: SME NOTES - None provided.\nCRITICAL: There are NO SME notes for this request. Do NOT use any notes from previous requests or conversations.\nProceed with Tiers 1 and 2 only. Ignore any notes that may have been mentioned in previous interactions.\n'}

${solution ? `Base Solution: ${solution}\n` : ''}${imageInfo ? `${imageInfo}\n` : ''}${uploadedImageInfo}
${curriculum && grade ? `Curriculum: ${curriculum} | Grade: ${grade} | Difficulty: ${difficulty}` : difficulty ? `Difficulty: ${difficulty}` : ''}
Subskills: ${subskillsText.substring(0, 200)}

TIER 2: Question-Specific Requirements - ${tier2Section}

${isImageBased ? `Characteristics: Questions that include or reference visual elements like graphs, diagrams, geometric figures, tables, or charts.

Apply These Additional Requirements:

1. Image Description Requirements (MANDATORY) For each generated question, you MUST provide:
- Complete visual description: Detailed text description of what the image contains
- All visual elements: Describe graphs, diagrams, tables, charts, geometric figures, equations shown in image form
- Labels and annotations: Include all axis labels, point coordinates, measurements, annotations visible
- Colors and styles: Mention line types (solid, dashed), colors if relevant to understanding
- Scale and units: Specify scales, gridlines, unit measurements shown

2. Image Description Format
Structure your descriptions clearly using this template:

FOR TABLES, DOT PLOTS, LINE PLOTS, BAR CHARTS, and other structured data:
- Present data in a clear tabular format using HTML table tags:
  Example for a table:
  "The image shows a data table:
  <table>
  <tr><th>Category</th><th>Value</th><th>Percentage</th></tr>
  <tr><td>A</td><td>25</td><td>25%</td></tr>
  <tr><td>B</td><td>30</td><td>30%</td></tr>
  <tr><td>C</td><td>45</td><td>45%</td></tr>
  </table>"

  Example for a dot plot or line plot:
  "The image shows a line graph with the following data points:
  <table>
  <tr><th>x</th><th>y</th><th>Label</th></tr>
  <tr><td>0</td><td>2</td><td>Start</td></tr>
  <tr><td>1</td><td>4</td><td></td></tr>
  <tr><td>2</td><td>6</td><td></td></tr>
  <tr><td>3</td><td>8</td><td>End</td></tr>
  </table>
  The graph has x-axis labeled 'Time (hours)' and y-axis labeled 'Distance (miles)'."

FOR GEOMETRIC SHAPES, DIAGRAMS, and non-tabular visuals:
- Use descriptive text format:
  "The image shows [type of visual: graph/triangle/table/etc.].
  [Describe main elements with labels].
  [List given measurements/values].
  [Note special markings or annotations].
  [State what needs to be found, indicated by variable or question mark]."

3. Mathematical Correctness Verification (CRITICAL - MUST VERIFY BEFORE DESCRIBING)
BEFORE writing any image description, you MUST verify that all measurements and relationships are mathematically correct:

FOR TRIANGLES:
- Triangle Inequality: Sum of any two sides > third side (a + b > c, a + c > b, b + c > a)
- Angle Sum: Sum of all angles = 180°
- Side-Angle Relationships: Use Law of Sines and Law of Cosines to verify consistency
  * Law of Sines: a/sin(A) = b/sin(B) = c/sin(C)
  * Law of Cosines: c² = a² + b² - 2ab*cos(C) (and variations)
- If given sides and angles, verify they satisfy all triangle relationships
- If given only sides, calculate angles using Law of Cosines and verify sum = 180°
- If given only angles, verify sum = 180° (sides can be scaled proportionally)
- Example verification: Triangle with sides 5, 5, 8 and angles 70°, 70°, 40°
  * Check angle sum: 70 + 70 + 40 = 180° ✓
  * Check triangle inequality: 5 + 5 > 8 (10 > 8) ✓, 5 + 8 > 5 (13 > 5) ✓, 5 + 8 > 5 ✓
  * Check Law of Sines: 5/sin(70°) ≈ 5.32, 8/sin(40°) ≈ 12.45 → NOT EQUAL → INVALID TRIANGLE
  * CORRECT: Either adjust angles to match sides OR adjust sides to match angles

FOR CIRCLES:
- Radius, diameter, circumference relationships: C = 2πr, d = 2r
- Arc length and central angle: arc = (θ/360°) × 2πr
- Sector area: area = (θ/360°) × πr²

FOR POLYGONS:
- Sum of interior angles: (n-2) × 180° for n-sided polygon
- Regular polygons: All sides and angles equal
- Verify side lengths and angles are consistent

FOR GRAPHS:
- Points must satisfy the equation: y = f(x)
- Coordinates must be consistent with scale and axis labels
- Slopes and intercepts must match the equation

FOR TABLES/CHARTS:
- Sums, averages, and relationships must be mathematically consistent
- Percentages must sum to 100% (if applicable)
- Data values must align with visual representation

CRITICAL PROCESS:
1. BEFORE writing the image description, calculate all relationships
2. Verify that all given measurements are mathematically consistent
3. If inconsistencies are found, adjust values to make them mathematically correct
4. Only then write the image description with verified correct values
5. DO NOT describe a figure that is mathematically impossible

EXAMPLE OF CORRECT PROCESS:
❌ WRONG: "Isosceles triangle with sides 5 cm, 5 cm, 8 cm and angles 70°, 70°, 40°"
   (This violates Law of Sines - sides don't match angles)

✅ CORRECT PROCESS:
   Step 1: Choose sides: 5 cm, 5 cm, 8 cm
   Step 2: Calculate angles using Law of Cosines:
     Angle opposite 8 cm: cos(C) = (5² + 5² - 8²)/(2×5×5) = (25+25-64)/50 = -14/50 = -0.28
     C = arccos(-0.28) ≈ 106.26°
   Step 3: Since isosceles, base angles = (180 - 106.26)/2 = 36.87° each
   Step 4: Verify: 36.87 + 36.87 + 106.26 = 180° ✓
   Step 5: Write description: "Isosceles triangle with two equal sides measuring 5 cm each, base measuring 8 cm, base angles measuring approximately 37° each, and vertex angle measuring approximately 106°."

OR

✅ ALTERNATIVE CORRECT PROCESS:
   Step 1: Choose angles: 70°, 70°, 40° (sum = 180° ✓)
   Step 2: Choose one side, say 5 cm
   Step 3: Use Law of Sines to calculate other sides:
     a/sin(70°) = b/sin(70°) = c/sin(40°) = 5/sin(70°) ≈ 5.32
     So: a = 5.32×sin(70°) ≈ 5 cm, b = 5.32×sin(70°) ≈ 5 cm, c = 5.32×sin(40°) ≈ 3.42 cm
   Step 4: Write description: "Isosceles triangle with two equal sides measuring 5 cm each, base measuring approximately 3.4 cm, base angles measuring 70° each, and vertex angle measuring 40°."

4. Logical and Realistic Feasibility
- Accurate representations: Graphs must follow mathematical rules (linear functions are straight lines, parabolas open correctly, etc.)
- Proportional accuracy: Visual proportions should match numerical values
- Realistic data: If showing real-world data (temperatures, prices), use plausible values
- Consistent scales: Axes and measurements must be mathematically consistent
- Physical possibility: Geometric figures must obey mathematical constraints (triangle inequality, angle sum properties, Pythagorean relationships)

5. Mathematical Accuracy in Visuals (MANDATORY VERIFICATION)
- CRITICAL: You MUST verify mathematical correctness BEFORE writing the image description
- Correct plotting: Points, lines, curves are mathematically accurate to the equations
- Valid constructions: Geometric figures can actually exist with given measurements - VERIFY THIS
- Data consistency: Table/chart values align with what's being asked
- Scale verification: If graph shows coordinates, they must be correctly positioned
- Angle accuracy: Marked angles must be mathematically consistent with side lengths
- Side-angle consistency: For triangles, verify Law of Sines and Law of Cosines
- Geometric constraints: All polygons must satisfy angle sum formulas and side relationships
- DO NOT describe any figure without first verifying all mathematical relationships
- If you cannot verify correctness, recalculate values until they are mathematically consistent

6. Completeness of Description
Your description must include:
- All given information: Every number, label, symbol visible in image
- Spatial relationships: "above," "below," "parallel to," "intersects at," "perpendicular to"
- Reference points: Origin, vertices, intercepts, maxima/minima, inflection points
- Grid information: If present, specify grid spacing and scale
- Legend/key: If the image has a legend, describe it fully

7. Types of Image-Based Questions
A. Geometric Diagrams - Triangles, circles, polygons, 3D shapes, composite figures
B. Graphs and Functions - Linear equations, parabolas, piecewise functions, systems of equations, transformations
C. Data Representations - Bar graphs, line graphs, pie charts, histograms, scatter plots, tables
D. Specialized Diagrams - Venn diagrams, number lines, probability trees, trigonometric unit circles

8. Distractor Logic for Image-Based Questions
Each distractor MUST have logic explaining VISUAL MISINTERPRETATION:
- "Misread angle measurement from protractor"
- "Counted wrong number of sides/shapes"
- "Misinterpreted graph scale or axis labels"
- "Read wrong value from table"
- "Confused similar-looking angles or lengths"
- "Misread coordinate points on graph"

9. Format Matching Requirements (CRITICAL - MUST MATCH BASE QUESTION FORMAT)
- CRITICAL: Your generated questions MUST match the EXACT format of the base question
- CRITICAL: The "question" field must contain the COMPLETE question stem - ALL sentences from the base question
- If the base question has multiple sentences (context, setup, then question), your generated question must have the SAME structure
- DO NOT truncate the question to just the last statement - include ALL sentences that appear in the base question
- If the base question is a word problem with a story, ALL generated questions must be word problems with stories
- If the base question uses specific phrasing like "Sarah has...", your questions should use similar phrasing with different names
- PRESERVE sentence structure: Match the grammatical patterns, sentence length, and complexity
- PRESERVE question format: If base asks "How many...?", all generated should ask "How many...?"
- PRESERVE context style: If base has a real-world scenario, all generated should have real-world scenarios
- PRESERVE formatting: Match punctuation, capitalization, and any special formatting
- ONLY vary: names, numbers, specific locations/objects, but keep the same structure
- The base question format is your template - follow it exactly

10. Image Variation Requirements (CRITICAL - MUST FOLLOW BASE QUESTION STRUCTURE)
- Each of the ${numQuestions} questions MUST have a DIFFERENT image description
- CRITICAL: ALL generated images must be the SAME TYPE as the base question (triangle → triangles, graph → graphs, table → tables, chart → charts)
- CRITICAL: ALL generated questions must ask the SAME TYPE of question as the base (area → area, angle → angle, value → value)
- CRITICAL: If the base question contains a TABLE, ALL ${numQuestions} copy questions MUST contain TABLES
- CRITICAL: If the base question contains a CHART (bar chart, line graph, dot plot, scatter plot, histogram), ALL ${numQuestions} copy questions MUST contain CHARTS of the SAME TYPE
- CRITICAL: The FIRST sentence of the image description determines the visual type - you MUST match it exactly
- CRITICAL: If base question image description starts with "The image shows a bar chart", ALL copy questions MUST start with "The image shows a bar chart" (NOT "The image shows a table" or "The image shows a data table")
- CRITICAL: If base question image description starts with "The image shows a line graph", ALL copy questions MUST start with "The image shows a line graph" (NOT "The image shows a table" or "The image shows a data table")
- CRITICAL: If base question image description starts with "The image shows a dot plot", ALL copy questions MUST start with "The image shows a dot plot" (NOT "The image shows a table")
- CRITICAL: If base question image description starts with "The image shows a scatter plot", ALL copy questions MUST start with "The image shows a scatter plot" (NOT "The image shows a table")
- CRITICAL: If base question image description starts with "The image shows a histogram", ALL copy questions MUST start with "The image shows a histogram" (NOT "The image shows a table" or "The image shows a bar chart")
- CRITICAL: DO NOT convert charts to tables - if the base question has a chart description, preserve the chart type in ALL copies
- CRITICAL: The opening sentence of the image description determines the visual type - match it exactly
- CRITICAL: If the base question contains a TABLE in HTML format (<table> tags), ALL copy questions MUST contain TABLES in HTML format
- CRITICAL: If the base question contains a CHART description (with table tags for chart data), ALL copy questions MUST contain CHART descriptions with table tags
- ONLY change the numerical values in the image description (measurements, angles, coordinates, table values, chart data points)
- Maintain the same visual structure, labels, and format as the base question
- Ensure all images are mathematically valid and consistent with their descriptions
- Do NOT repeat the same image description across questions
- Do NOT change the image type, question type, or add new visual elements not in the base question
- Do NOT remove tables or charts from copy questions if they exist in the base question
- Do NOT add tables or charts to copy questions if they don't exist in the base question
- Use the base question's image description as a template - follow its exact structure and format

10.5. Table and Chart Preservation Requirements (CRITICAL - FOR QUESTIONS WITH TABLES OR CHARTS)
${(notes && (notes.toLowerCase().includes('table') || notes.toLowerCase().includes('chart'))) || (images && (images.toLowerCase().includes('<table>') || images.toLowerCase().includes('chart') || images.toLowerCase().includes('bar chart') || images.toLowerCase().includes('line graph') || images.toLowerCase().includes('dot plot') || images.toLowerCase().includes('scatter plot') || images.toLowerCase().includes('histogram'))) || (baseQuestion && (baseQuestion.toLowerCase().includes('table') || baseQuestion.toLowerCase().includes('chart'))) || (images && images.match(/The image shows a (bar chart|line graph|dot plot|scatter plot|histogram)/i)) ? `- CRITICAL: This question involves a TABLE or CHART, and SME notes may contain variation instructions
- CRITICAL: FIRST, identify the chart type from the base question's image description by looking at the FIRST sentence
- CRITICAL: Check if the base question image description starts with one of these EXACT phrases:
  * "The image shows a bar chart" → ALL copies must say "The image shows a bar chart"
  * "The image shows a line graph" → ALL copies must say "The image shows a line graph"
  * "The image shows a dot plot" → ALL copies must say "The image shows a dot plot"
  * "The image shows a scatter plot" → ALL copies must say "The image shows a scatter plot"
  * "The image shows a histogram" → ALL copies must say "The image shows a histogram"
  * "The image shows a data table" or just "<table>" → ALL copies must have tables
- CRITICAL: If the base question image description contains a TABLE (HTML <table> tags), ALL ${numQuestions} copy questions MUST contain TABLES with the same structure
- CRITICAL: If the base question image description contains a CHART (bar chart, line graph, dot plot, scatter plot, or histogram with table data), ALL ${numQuestions} copy questions MUST contain CHARTS of the SAME TYPE
- CRITICAL: Preserve the table/chart structure: If base has a table with 3 columns, all copies should have tables with 3 columns
- CRITICAL: Preserve the chart type: If base has a bar chart, all copies should have bar charts (NOT line graphs or other types)
- CRITICAL: Preserve the chart type: If base has a line graph, all copies should have line graphs (NOT bar charts, NOT tables)
- CRITICAL: Preserve HTML table format: If base uses <table> tags, all copies must use <table> tags
- CRITICAL: Preserve chart description format: If base describes a chart with "The image shows a bar chart..." and includes a table, all copies must follow the same format
- CRITICAL: Preserve chart description format: If base describes a chart with "The image shows a line graph..." and includes a table, all copies must follow the same format
- EXAMPLE OF CORRECT CHART PRESERVATION:
  Base question image: "The image shows a line graph titled 'Sales by Month'.\nThe x-axis is labeled 'Month' and y-axis is labeled 'Sales ($)'.\nThe data points are:\n<table>..."
  ✅ CORRECT copy: "The image shows a line graph titled 'Revenue by Quarter'.\nThe x-axis is labeled 'Quarter' and y-axis is labeled 'Revenue ($)'.\nThe data points are:\n<table>..."
  ❌ WRONG copy: "The image shows a data table:\n<table>..." (This is WRONG - it's a table, not a line graph)
  ❌ WRONG copy: "The image shows a bar chart..." (This is WRONG - base has line graph, copy must have line graph)
- CRITICAL: Always check the FIRST sentence of the base question's image description - if it says "bar chart", "line graph", "dot plot", "scatter plot", or "histogram", your copy MUST also say the same chart type
- CRITICAL: You MUST follow ALL table variation instructions specified in SME notes (if provided)
- Table variation instructions in SME notes may specify:
  * Value ranges for different difficulty levels (e.g., "Easy: 1-20", "Medium: 21-50", "Hard: 51-100")
  * Number types (e.g., "Use whole numbers only", "Include decimals", "Use percentages", "Use fractions")
  * Column variations (e.g., "Vary category names", "Keep same column structure", "Change column headers")
  * Row count variations (e.g., "Easy: 3 rows", "Medium: 4 rows", "Hard: 5 rows")
  * Value constraints (e.g., "Values should be multiples of 5", "Use even numbers only", "Values between 10-100")
  * Mathematical relationships (e.g., "Percentages must sum to 100%", "Values must be consistent with totals")
- When generating tables:
  * Parse and apply ALL variation instructions from SME notes
  * Ensure each of the ${numQuestions} questions has DIFFERENT table values
  * Maintain the same table structure (columns, headers) as the base question unless SME notes specify otherwise
  * Only vary the data values according to SME notes specifications
  * If SME notes specify difficulty-based ranges, apply them based on the question's difficulty level
- When generating charts:
  * CRITICAL: First, identify the chart type from the base question's image description
  * CRITICAL: Look for these EXACT phrases in the FIRST sentence of the base question image description:
    - "The image shows a bar chart" → ALL copies must say "The image shows a bar chart"
    - "The image shows a line graph" → ALL copies must say "The image shows a line graph"
    - "The image shows a dot plot" → ALL copies must say "The image shows a dot plot"
    - "The image shows a scatter plot" → ALL copies must say "The image shows a scatter plot"
    - "The image shows a histogram" → ALL copies must say "The image shows a histogram"
  * CRITICAL: If base question has a bar chart, ALL ${numQuestions} copy questions MUST have bar charts
  * CRITICAL: If base question has a line graph, ALL ${numQuestions} copy questions MUST have line graphs
  * CRITICAL: If base question has a dot plot, ALL ${numQuestions} copy questions MUST have dot plots
  * CRITICAL: If base question has a scatter plot, ALL ${numQuestions} copy questions MUST have scatter plots
  * CRITICAL: If base question has a histogram, ALL ${numQuestions} copy questions MUST have histograms
  * CRITICAL: DO NOT generate "The image shows a data table" when the base says "The image shows a line graph"
  * CRITICAL: DO NOT generate "The image shows a data table" when the base says "The image shows a bar chart"
  * CRITICAL: DO NOT change chart types - if base has line graph, copies must have line graph (NOT bar chart, NOT table)
  * CRITICAL: DO NOT change chart types - if base has bar chart, copies must have bar chart (NOT line graph, NOT table)
  * Maintain the same chart structure (axis labels, title format) as the base question
  * Only vary the data points/values in the chart, NOT the chart type
  * Preserve the chart description format (e.g., "The image shows a line graph..." followed by table data)
  * Preserve the chart description format (e.g., "The image shows a bar chart..." followed by table data)
  * Ensure each of the ${numQuestions} questions has DIFFERENT chart data values
- Examples of SME notes for table variations:
  * "Table variations: Easy questions use values 1-20, Medium: 21-50, Hard: 51-100"
  * "Table values should be multiples of 5 and whole numbers only"
  * "Vary category names (A, B, C can become X, Y, Z) but keep same column structure"
  * "Easy: 3 rows, Medium: 4 rows, Hard: 5 rows. All values should be between 10-100"
  * "Keep same columns (Category, Value, Percentage). Vary values but ensure percentages sum to 100%"
- CRITICAL: If SME notes specify table variations, you MUST follow them exactly
- CRITICAL: Each generated table must have unique values that differ from:
  * The base question's table values
  * All other generated questions' table values
- CRITICAL: Maintain mathematical consistency (e.g., if percentages are used, they should sum correctly)
- If no table variation instructions are in SME notes, vary values naturally while maintaining the same structure` : `- For questions with tables: Vary numerical values while maintaining the same table structure and column headers as the base question
- Ensure each generated table has different values from the base question and other generated questions`}

11. Context Diversity for Image-Based Questions (CRITICAL - FOR WORD PROBLEMS WITH CONTEXT)
${baseQuestion.match(/context|scenario|situation|story|real-world|real life|everyday|daily|life|has|bought|sold|traveled|drove|walked|ran|spent|earned|saved|collected|gathered|planted|harvested|baked|cooked|made|built|painted|drew|wrote|read|studied|played|won|lost|gave|received|shared|divided|combined|mixed|poured|filled|emptied|weighed|measured|counted|found|discovered|created|designed|constructed/i) ? `- CRITICAL: The base question contains a context/scenario/story (word problem format)
- CRITICAL: Each of the ${numQuestions} generated questions MUST have a DIFFERENT context from the base question
- CRITICAL: NO CONTEXT REPETITION: All ${numQuestions} questions must have UNIQUE contexts - no two questions can share the same context
- CRITICAL: Maintain the EXACT same format and structure as the base question while changing ONLY the context
- Context diversity examples:
  * If base mentions "Sarah's garden", generated contexts could be: "Maria's farm", "Tom's backyard", "Lisa's park", "John's field", etc.
  * If base mentions "a store", generated contexts could be: "a bakery", "a library", "a school", "a museum", "a restaurant", etc.
  * If base mentions "a journey", generated contexts could be: "a race", "a delivery", "a hike", "a commute", "a trip", etc.
- Varied contexts: Draw from diverse real-life situations (shopping, travel, construction, cooking, sports, finance, school, nature, work, hobbies, family, community)
- Different characters: Use diverse names, professions, ages, and settings
- Different locations: Vary settings (home, school, park, store, office, etc.)
- Different time periods: Vary temporal contexts (morning, afternoon, seasons, etc.)
- CRITICAL: Maintain the same mathematical structure and question type while changing ONLY the context
- CRITICAL: The context must be relevant to the mathematical problem being solved
- CRITICAL: PRESERVE THE EXACT FORMAT: If the base question uses "Sarah has X and buys Y, how many...?", your generated questions should use the SAME sentence structure with different names and numbers
- CRITICAL: Verify that each of the ${numQuestions} questions has a UNIQUE context that differs from:
  * The base question's context
  * All other generated questions' contexts
- Example: If generating 20 questions, you must create 20 completely different contexts/scenarios
- DO NOT reuse contexts: Each question must have its own unique story/situation
- FORMAT MATCHING: Your generated questions must match the base question's format exactly:
  * Same sentence structure
  * Same question phrasing
  * Same grammatical patterns
  * Same level of detail
  * Only change: names, numbers, and specific context details` : '- If the base question does not contain a context/scenario, maintain that format (no context needed)'}` : `Characteristics: Mathematical concepts embedded in real-life scenarios, stories, or contexts.

Apply These Additional Requirements:

1. Scenario Diversity (CRITICAL)
- NO REPETITION: Never use the same context/scenario multiple times
- Varied contexts: Draw from diverse real-life situations (shopping, travel, construction, cooking, sports, finance, school, nature, work)
- Different characters: Use diverse names, professions, ages, and settings
- Rotate problem types: Mix distance-time, work-rate, mixture, age, money, and measurement problems

1.1 Answer Value Diversity (CRITICAL - MUST BE DIFFERENT)
- CRITICAL: Each generated copy question MUST have a DIFFERENT correct answer value than the base question
- If the base question's correct answer is 25%, NONE of the copy questions should have 25% as the correct answer
- If the base question's correct answer is $50, NONE of the copy questions should have $50 as the correct answer
- If the base question's correct answer is 12 apples, NONE of the copy questions should have 12 apples as the correct answer
- Each copy question must have a UNIQUE correct answer value that is different from the base question and different from other copy questions
- Change the numbers, quantities, percentages, amounts, etc. in each question to ensure different answer values
- Example: Base question answer = 25% → Copy questions should have answers like 30%, 20%, 35%, 15%, etc. (NOT 25%)
- Example: Base question answer = $50 → Copy questions should have answers like $60, $45, $75, $40, etc. (NOT $50)
- CRITICAL: Verify that each generated question's correct answer is different from the base question's answer

2. Logical and Realistic Feasibility
- Real-world plausibility: Scenarios must be believable and possible
- Reasonable speeds, prices, timeframes
- Consistent units: Quantities must make practical sense
- Age appropriateness: Ages must be realistic for activities described
- Economic sensibility: Prices and monetary values should reflect reality
- Physical constraints: Respect real-world limitations

3. Phrasing Consistency (CRITICAL - SENTENCE STRUCTURE PRESERVATION)
- Match the base question's style (formal/conversational)
- ⚠️⚠️⚠️ CRITICAL: PRESERVE SENTENCE STRUCTURE ⚠️⚠️⚠️: Maintain the EXACT same grammatical patterns, sentence complexity, and word order structure as the base question
- Keep the same sentence flow: If base question uses "A person has X and buys Y, how many...?" maintain this structure
- Maintain parallel construction: If base uses compound sentences, use compound sentences; if simple, use simple
- Consistent terminology: Use similar vocabulary level and mathematical language
- Same level of detail: Match the amount of contextual information provided
- Parallel question format: If base asks "How many...?" frame variants similarly
- ⚠️⚠️⚠️ CRITICAL: The sentence structure must remain the SAME - only change the numbers, names, and context, NOT the grammatical structure ⚠️⚠️⚠️
- DO NOT change: sentence length, clause structure, question format, verb forms, or grammatical complexity
- DO NOT add or remove: conjunctions, prepositions, or structural elements
- EXAMPLE: If base question is "Sarah has 5 apples. She buys 7 more. How many apples does she have now?"
  ✅ CORRECT: "Tom has 8 books. He buys 3 more. How many books does he have now?" (same structure)
  ❌ WRONG: "Tom bought 3 more books to add to his collection of 8 books. What is the total?" (different structure)
  ❌ WRONG: "How many books does Tom have after buying 3 more when he started with 8?" (different structure)

4. Mathematical Accuracy in Context
- Verify all calculations produce valid, sensible answers
- Ensure given data leads to solvable problems
- Check that conditions don't contradict each other
- Confirm answers align with the scenario's logic

5. Clear Problem Setup
- Unambiguous wording: Reader should understand exactly what's being asked
- All necessary information: Include every detail needed to solve
- No extraneous data: Unless specifically testing data filtering skills
- Defined relationships: Clearly state how variables relate to each other

6. Completeness Check
- All units are specified (km, hours, dollars, liters, kg, etc.)
- Question clearly states what to find
- Timeframes are logical (before/after relationships make sense)
- Quantities are properly quantified (not vague like "some" or "few")

7. Common Pitfalls to AVOID
❌ Impossible scenarios (student solving 200 problems in 5 minutes)
❌ Anachronisms (using outdated prices or technologies inappropriately)
❌ Stereotypes (gender, cultural, or occupational stereotyping)
❌ Overly complex contexts (story overshadowing the math)
❌ Ambiguous pronouns (unclear referents for "he," "she," "it," "they")`}

CRITICAL REQUIREMENTS FOR OPTIONS AND CORRECT ANSWERS:

1. OPTIONS FORMAT:
   - Each option MUST have a "text" field containing a COMPLETE, MEANINGFUL answer
   - DO NOT use placeholder text like "Option A", "Option B", "Choice A", etc.
   - Each option MUST be a real, complete answer that a student could choose
   - Options should be in the same format as the base question's options

2. CORRECT ANSWER (CRITICAL - MUST BE VERIFIED):
   - ONE and ONLY ONE option per question MUST have "logic": "CA" (Correct Answer)
   - CRITICAL: You MUST solve each question completely before marking the correct answer
   - The correct answer MUST be mathematically correct - verify by solving the problem step-by-step
   - Work backward from your answer to confirm it satisfies all conditions in the question
   - The correct answer MUST follow all SME notes requirements
   - Mark the correct answer clearly with "logic": "CA" - DO NOT mark incorrect answers as CA
   - If you are unsure which answer is correct, solve the problem completely first, then mark the verified correct answer
   
   VERIFICATION PROCESS (MANDATORY - FOLLOW THESE STEPS):
   Step 1: Read the question carefully and identify what is being asked
   Step 2: Solve the problem completely step-by-step (show your work mentally)
   Step 3: Calculate the final answer
   Step 4: Verify your answer by plugging it back into the problem or checking it
   Step 5: Check that your answer satisfies all conditions in the question
   Step 6: Only then, mark the option with your verified answer as "logic": "CA"
   Step 7: Generate distractors (incorrect options) with appropriate logic
   
   EXAMPLE OF CORRECT PROCESS:
   Question: "What is 15 + 27?"
   Step 1: Identify: Addition problem
   Step 2: Solve: 15 + 27 = 42
   Step 3: Verify: 42 - 15 = 27 ✓ (correct)
   Step 4: Mark option with "42" as "logic": "CA"
   Step 5: Generate distractors: "40" (logic: "Forgot to add ones"), "43" (logic: "Added incorrectly"), etc.
   
   ❌ WRONG: Marking "40" as CA because it's close to the answer
   ❌ WRONG: Marking the first option as CA without solving
   ❌ WRONG: Marking multiple options as CA
   ❌ WRONG: Guessing which answer is correct
   ✅ CORRECT: Solving completely, verifying, then marking only the verified correct answer as CA

3. INCORRECT OPTIONS (DISTRACTORS):
   - Each incorrect option MUST have a "logic" field explaining the error
   - Logic must be SHORT (3-6 words) describing the mistake
   - ${isImageBased ? 'For image-based: Logic should describe VISUAL MISINTERPRETATION' : 'For word problems: Logic should describe ACTUAL ERRORS students would make'}
   - Examples: "Added instead of multiplied", "Forgot to carry over", "Wrong denominator", "Calculation error"${isImageBased ? ', "Misread angle measurement", "Counted wrong number of sides"' : ''}

4. OPTIONS COUNT:
   - Each question MUST have EXACTLY ${numOptions} options
   - All ${numOptions} options must be complete and valid answers

5. STEP-BY-STEP SOLUTIONS (CRITICAL - MUST BE COMPLETE AND DETAILED):
   - Each question MUST include a COMPLETE, DETAILED step-by-step solution in the "solution" field
   - CRITICAL: The solution MUST be complete in all sense - show ALL steps, calculations, and reasoning
   - ⚠️⚠️⚠️ CRITICAL FORMATTING REQUIREMENT ⚠️⚠️⚠️: Format each step on a NEW LINE using "Step 1:", "Step 2:", "Step 3:", etc.
   - ⚠️⚠️⚠️ YOU MUST USE \n (newline character) BETWEEN EACH STEP - DO NOT PUT MULTIPLE STEPS ON THE SAME LINE ⚠️⚠️⚠️
   - Each step MUST be clearly separated and on its own line for readability
   - Include ALL intermediate calculations and explanations
   - Show the complete work from start to finish - do NOT skip steps
   - Verify the final answer matches the correct option
   ${isImageBased ? '- Reference specific parts of the image description (e.g., "Step 1: Using the angle shown in the triangle...", "Step 2: From the graph, we can see...")' : '- Show the logical progression from the problem statement to the final answer with ALL steps'}
   - Make it educational and easy to follow - a student should be able to understand each step
   - Format: Use line breaks between steps (each step on a new line)
   ${solution ? '- Base the solution on the provided base solution, adapting steps to match each question\'s numbers/context' : ''}
   - Example format (CRITICAL: Each step MUST be on a separate line with \n):
     "Step 1: [First step explanation and calculation]\nStep 2: [Second step explanation and calculation]\nStep 3: [Final step and answer]"
   - CRITICAL: You MUST use \n (newline character) between each step - do NOT put multiple steps on the same line

QUALITY CHECKLIST (Self-Verify Before Finalizing):
✅ Format matches base question exactly
✅ ${isImageBased ? 'CRITICAL: Question field contains COMPLETE question stem with ALL sentences from base question format (not just the last question statement)' : ''}
✅ Correct answer is mathematically verified
✅ Options don't follow a predictable pattern
✅ CRITICAL: Number of options is EXACTLY ${numOptions} - count them to verify!
✅ ${isImageBased ? 'Complete visual description provided for each question' : 'Scenario is different from base and realistic'}
✅ ${isImageBased ? 'Description allows problem to be solved' : 'CRITICAL: Sentence structure EXACTLY matches base question (same grammatical patterns, word order, sentence complexity, and structure)'}
✅ ${isImageBased ? 'CRITICAL: Image type matches base question (triangle → triangles, graph → graphs, etc.)' : ''}
✅ ${isImageBased ? 'CRITICAL: Question format matches base question (area → area, angle → angle, etc.)' : ''}
✅ ${isImageBased ? 'CRITICAL: Only numerical values changed, not image structure or question type' : ''}
✅ ${isImageBased ? 'CRITICAL: All measurements in image description are mathematically correct (triangle angles sum to 180°, Law of Sines/Cosines satisfied, etc.)' : ''}
✅ ${isImageBased ? '' : 'CRITICAL: Each copy question has a DIFFERENT correct answer value than the base question - verify this!'}
${isImageBased && ((notes && notes.toLowerCase().includes('table')) || (images && images.toLowerCase().includes('<table>')) || (baseQuestion && baseQuestion.toLowerCase().includes('table'))) ? '✅ CRITICAL: If SME notes specify table variation instructions, ALL table values follow those specifications (ranges, constraints, row counts, etc.)\n✅ CRITICAL: Table values are different from the base question and all other generated questions\n✅ CRITICAL: Table structure (columns, headers) matches the base question unless SME notes specify otherwise\n✅ CRITICAL: If percentages are in the table, they sum to 100% correctly\n' : ''}
${isImageBased && ((notes && notes.toLowerCase().includes('chart')) || (images && (images.toLowerCase().includes('bar chart') || images.toLowerCase().includes('line graph') || images.toLowerCase().includes('dot plot') || images.toLowerCase().includes('scatter plot') || images.toLowerCase().includes('histogram')))) ? '✅ CRITICAL: Chart type matches base question (line graph → line graphs, bar chart → bar charts, etc.)\n✅ CRITICAL: Image description starts with the same chart type phrase as base question\n✅ CRITICAL: Chart has NOT been converted to a table\n✅ CRITICAL: Chart data values are different from base question and other generated questions\n' : ''}
✅ CRITICAL: ALL SME notes (if provided) have been followed PRECISELY - verify each requirement individually
✅ CRITICAL: Solution is COMPLETE with ALL steps shown - verify no steps are skipped
✅ CRITICAL: Solution is formatted with each step on a new line for readability
✅ No mathematical errors or logical contradictions

⚠️⚠️⚠️ FINAL REMINDER - ANSWER VERIFICATION:
Before generating your response, ensure you have:
1. Solved each question completely step-by-step
2. Verified your answer is mathematically correct
3. Checked that your answer satisfies all conditions
4. Marked ONLY the verified correct answer as "logic": "CA"
5. Generated appropriate distractors with error logic
${isImageBased ? '' : '6. CRITICAL: Verified that each copy question has a DIFFERENT correct answer value than the base question (e.g., if base answer is 25%, copy questions should have 30%, 20%, 35%, etc., NOT 25%)'}

DO NOT:
- Mark an answer as CA without solving the problem
- Mark multiple options as CA
- Guess which answer is correct
- Mark the first option as CA just because it's first
${isImageBased ? '' : '- Use the same answer value as the base question for any copy question'}

CRITICAL JSON FORMAT REQUIREMENTS:
- Your FIRST character MUST be [ (opening square bracket)
- Your LAST character MUST be ] (closing square bracket)
- Return ONLY a valid JSON array starting with [ and ending with ]
- DO NOT start with { (curly brace) - that means a single object, which is WRONG
- DO NOT return a single object - you MUST return an array
- NO markdown code blocks (no \`\`\`json or \`\`\`)
- NO explanations or text before or after the JSON
- NO comments or notes
- Start response immediately with [
- End response with ]
- Ensure all strings are properly quoted with double quotes
- Ensure all brackets and braces are properly matched
- Do NOT include any text outside the JSON array

⚠️⚠️⚠️ CRITICAL: You MUST return EXACTLY ${numQuestions} question objects in a JSON array. DO NOT return only one question.

Each question object MUST have this structure:
${isImageBased ? `{
  "image": "[Detailed image description with sides, angles, equations, table values, etc.]",
  "question": "[COMPLETE question stem - include ALL sentences from the base question format, not just the question part. If the base question has context/setup sentences, include them all. Example: 'Sarah has a rectangular garden. The length is 5 meters and the width is 3 meters. What is the area of the garden?']",
  "solution": "Step 1: [First step with reference to image elements]\nStep 2: [Second step]\nStep 3: [Final step]",
  "options": [
    {"text": "[Correct answer value]", "logic": "CA"},
    {"text": "[Distractor 1 value]", "logic": "[Visual misinterpretation that leads to this]"},
    ...
  ]
}` : `{
  "question": "[Question text]",
  "options": [
    {"text": "[Correct answer]", "logic": "CA"},
    {"text": "[Distractor 1]", "logic": "[Error description]"},
    ...
  ],
  "image": "",
  "solution": "Step 1: [First step]\nStep 2: [Second step]\nStep 3: [Final step]"
}`}

CRITICAL: Each "options" array MUST contain EXACTLY ${numOptions} option objects:
- ONE option with "logic": "CA" (the correct answer)
- ${numOptions - 1} distractors, each with logic explaining the error${isImageBased ? ' or visual misinterpretation' : ''}

Example of correct options format:
"options": [
  {"text": "${isImageBased ? '45°' : '5 + 7'}", "logic": "CA"},
  {"text": "${isImageBased ? '30°' : '5 - 7'}", "logic": "${isImageBased ? 'Misread angle measurement from protractor' : 'Used subtraction instead'}"},
  {"text": "${isImageBased ? '60°' : '5 × 7'}", "logic": "${isImageBased ? 'Confused complementary angle' : 'Used multiplication instead'}"}
]

DO NOT return placeholder text like "Option A", "Option B", etc. Each option MUST be a complete, valid answer choice.

Your response should look like this (example for ${numQuestions} questions):
[${isImageBased ? `{
  "image": "A right triangle with sides labeled: base = 3 cm, height = 4 cm, hypotenuse = 5 cm.",
  "question": "A right triangle is shown with a base of 3 cm and height of 4 cm. What is the area of the triangle?",
  "solution": "Step 1: Identify the base and height from the image. Base = 3 cm, Height = 4 cm.\nStep 2: Apply area formula: Area = (1/2) × base × height = (1/2) × 3 × 4 = 6 cm²",
  "options": [
    {"text": "6 cm²", "logic": "CA"},
    {"text": "12 cm²", "logic": "Forgot to multiply by 1/2"},
    {"text": "7 cm²", "logic": "Added base and height instead of multiplying"},
    {"text": "5 cm²", "logic": "Used hypotenuse length instead of height"}
  ]
}` : `{
  "question": "Sarah had 5 apples. She picked 7 more apples. Write an expression to represent the total number of apples Sarah has now.",
  "options": [
    {"text": "5 + 7", "logic": "CA"},
    {"text": "5 - 7", "logic": "Used subtraction instead"},
    {"text": "5 × 7", "logic": "Used multiplication instead"},
    {"text": "7 - 5", "logic": "Reversed the order"}
  ],
  "image": "",
  "solution": "Step 1: [First step]\nStep 2: [Second step]\nStep 3: [Final step]"
}`}, ...]

CRITICAL FINAL REMINDER:
- You MUST return EXACTLY ${numQuestions} questions in the JSON array
- CRITICAL: Each question MUST have EXACTLY ${numOptions} options - NO MORE, NO LESS
- CRITICAL: Each solution MUST have steps on SEPARATE LINES using \n - do NOT put multiple steps on the same line
- CRITICAL: Solution format must be: "Step 1: ...\nStep 2: ...\nStep 3: ..." (with \n between each step)
${isImageBased ? '' : '- CRITICAL: Verify that sentence structure EXACTLY matches the base question (same grammatical patterns, word order, and sentence complexity)'}
${isImageBased ? '' : '- CRITICAL: Only change numbers, names, and context - DO NOT change sentence structure, grammatical patterns, or word order'}
- CRITICAL: Before marking any option as "CA", verify that the answer format matches ALL SME notes requirements
- CRITICAL: If SME notes specify answer format (mixed number, simplified fraction, etc.), the correct answer MUST be in that exact format
- Count your questions: The array must have exactly ${numQuestions} elements, no more, no less
- Count options in EACH question: Every question must have exactly ${numOptions} options
- Verify before submitting: Check that your JSON array contains exactly ${numQuestions} question objects
- Verify before submitting: Check that EACH question object has exactly ${numOptions} options in its options array
- Verify before submitting: Check that EACH solution has steps separated by \n (newline characters)
- Verify before submitting: Check that EACH correct answer (marked with "CA") matches ALL SME notes format requirements
${isImageBased ? '' : '- Verify before submitting: Check that EACH question has the SAME sentence structure as the base question'}
- The array must start with [ and end with ]
- DO NOT return fewer than ${numQuestions} questions
- DO NOT return more than ${numQuestions} questions
- DO NOT add extra options or remove options - the count must match exactly
- DO NOT put multiple solution steps on the same line - each step MUST be on its own line with \n
- DO NOT ignore SME notes format requirements - if SME notes specify a format, the correct answer MUST match it
${isImageBased ? '' : '- DO NOT change sentence structure, grammatical patterns, or word order - only change numbers, names, and context'}
- ${notes && notes.length > 0 ? 'CRITICAL: Verify that ALL SME notes requirements have been followed in EVERY question, including answer format requirements' : ''}`
  }
  
  try {
    // Get maximum tokens supported by the model
    const aiProvider = getAIProvider(model)
    let maxModelTokens = 16384 // Default for OpenAI models (GPT-4o, GPT-4 Turbo, GPT-3.5 Turbo)
    if (aiProvider === 'gemini') {
      maxModelTokens = 8192 // Gemini models typically support 8192 output tokens
    } else if (aiProvider === 'nararouter') {
      maxModelTokens = 8192
    }
    
    // Calculate tokens needed
    const tokensPerQuestion = Math.max(500, 400 * numOptions)
    let tokensNeeded = Math.max(1500, tokensPerQuestion * numQuestions)
    
    // Increase token limit for larger question counts
    // For 10+ questions, we need significantly more tokens
    if (numQuestions >= 10) {
      tokensNeeded = Math.min(maxModelTokens, Math.floor(tokensPerQuestion * numQuestions * 1.5))
    } else if (numQuestions > 5) {
      tokensNeeded = Math.min(maxModelTokens, Math.floor(tokensPerQuestion * numQuestions * 1.3))
    } else {
    tokensNeeded = Math.min(8000, tokensNeeded)
    }
    
    if (numQuestions > 1) {
      tokensNeeded = Math.floor(tokensNeeded * 1.2)
    }
    
    // Adjust tokens for image-based questions
    // Since image analysis is done separately via analyzeImageForQuestion,
    // we can use fewer tokens as the image description is already provided
    if (questionType === 'image_based' && imageFiles.length > 0) {
      // Reduce tokens for image-based since image description is already provided
      // The model doesn't need to analyze images, just generate questions from the description
      if (numQuestions >= 10) {
        tokensNeeded = Math.min(maxModelTokens, Math.floor(tokensNeeded * 0.9)) // 10% reduction
      } else {
        tokensNeeded = Math.min(maxModelTokens, Math.floor(tokensNeeded * 0.85)) // 15% reduction
      }
    }
    
    // Final cap to ensure we never exceed model's maximum
    tokensNeeded = Math.min(maxModelTokens, tokensNeeded)
    
    // Set temperature based on question type
    // For mathematical questions: 0.5 for more deterministic, precise answers
    // For word problems: 0.9 (within 0.6-1.2 range) to maintain sentence structure while allowing variation
    // For image-based: 0.7 (default)
    let temperature = 0.7
    if (questionType === 'mathematical') {
      temperature = 0.5
    } else if (questionType === 'word_problem') {
      temperature = 0.9 // Middle of 0.6-1.2 range to balance creativity with structure preservation
    }
    
    // Check if model supports vision and we have images
    const provider = getAIProvider(model)
    let supportsVision = false
    let shouldIncludeImages = false
    
    if (provider === 'openai') {
      supportsVision = model === 'gpt-4o' || model === 'gpt-4-turbo' || model === 'gpt-4-turbo-preview'
    } else if (provider === 'nararouter') {
      supportsVision = doesNaraModelSupportVision(model)
    } else {
      // Gemini models support vision
      supportsVision = model.startsWith('gemini-')
    }
    
    shouldIncludeImages = questionType === 'image_based' && imageFiles.length > 0 && supportsVision
    
    // Use unified AI client
    let content: string
    try {
      content = await generateWithAI(
        systemPrompt,
        userPrompt,
        model,
        temperature,
        tokensNeeded,
        shouldIncludeImages ? imageFiles : undefined
      )
    } catch (error: any) {
      // If model is not available, fallback to gpt-4o (for OpenAI models) or gemini-1.5-pro (for Gemini)
      if (error?.message?.includes('model') || error?.code === 'model_not_found') {
        const provider = getAIProvider(model)
        let fallbackModel = 'gpt-4o'
        if (provider === 'gemini') {
          fallbackModel = 'gemini-1.5-pro'
        } else if (provider === 'nararouter') {
          fallbackModel = 'agnes-3-flash'
        }
        console.warn(`${model} not available, falling back to ${fallbackModel}`)
        content = await generateWithAI(
          systemPrompt,
          userPrompt,
          fallbackModel,
          temperature,
          tokensNeeded,
          shouldIncludeImages ? imageFiles : undefined
        )
      } else {
        throw error
      }
    }
    
    if (!content || content.trim().length === 0) {
      throw new Error('AI returned empty content')
    }
    
    // Parse JSON from response
    let cleanedContent = content.trim()
    cleanedContent = cleanedContent.replace(/```json\s*/g, '')
    cleanedContent = cleanedContent.replace(/```\s*/g, '')
    cleanedContent = cleanedContent.trim()
    
    // Extract JSON array
    const firstBracket = cleanedContent.indexOf('[')
    const lastBracket = cleanedContent.lastIndexOf(']')
    
    if (firstBracket === -1 || lastBracket === -1 || lastBracket <= firstBracket) {
      console.error('Failed to find JSON array. Content preview:', cleanedContent.substring(0, 500))
      throw new Error('Failed to find JSON array in response. The AI may not have returned questions in the expected format.')
    }
    
    const jsonContent = cleanedContent.substring(firstBracket, lastBracket + 1)
    
    // Sanitize JSON: Escape unescaped control characters in string values
    // This fixes issues where AI includes literal newlines, tabs, etc. instead of escaped versions
    let sanitizedJson = jsonContent
    try {
      // More robust approach: process character by character to handle escaped sequences correctly
      let result = ''
      let inString = false
      let escapeNext = false
      
      for (let i = 0; i < jsonContent.length; i++) {
        const char = jsonContent[i]
        
        if (escapeNext) {
          result += char
          escapeNext = false
          continue
        }
        
        if (char === '\\') {
          result += char
          escapeNext = true
          continue
        }
        
        if (char === '"') {
          // Check if this quote is escaped by counting backslashes
          let backslashCount = 0
          for (let j = i - 1; j >= 0 && jsonContent[j] === '\\'; j--) {
            backslashCount++
          }
          // If even number of backslashes (or zero), the quote is not escaped
          if (backslashCount % 2 === 0) {
            inString = !inString
          }
          result += char
          continue
        }
        
        if (inString) {
          // We're inside a string value - escape control characters
          if (char === '\n') {
            result += '\\n'
          } else if (char === '\r') {
            result += '\\r'
          } else if (char === '\t') {
            result += '\\t'
          } else if (char === '\f') {
            result += '\\f'
          } else if (char === '\b') {
            result += '\\b'
          } else if (char.charCodeAt(0) < 0x20 || char.charCodeAt(0) === 0x7F) {
            // Other control characters - remove them
            continue
          } else {
            result += char
          }
        } else {
          result += char
        }
      }
      
      sanitizedJson = result
    } catch (sanitizeError) {
      console.warn('JSON sanitization failed, attempting parse with original:', sanitizeError)
      sanitizedJson = jsonContent
    }
    
    let parsed
    try {
      parsed = JSON.parse(sanitizedJson)
    } catch (parseError: any) {
      console.error('JSON parse error:', parseError.message)
      console.error('Sanitized JSON preview:', sanitizedJson.substring(0, 500))
      console.error('Original JSON preview:', jsonContent.substring(0, 500))
      
      // Try one more time with more aggressive sanitization
      try {
        // Remove or escape any remaining control characters
        const aggressiveSanitized = sanitizedJson.replace(/[\x00-\x1F\x7F]/g, (char) => {
          const code = char.charCodeAt(0)
          if (code === 0x0A) return '\\n'  // \n
          if (code === 0x0D) return '\\r'  // \r
          if (code === 0x09) return '\\t'  // \t
          if (code === 0x0C) return '\\f'  // \f
          if (code === 0x08) return '\\b'  // \b
          return '' // Remove other control characters
        })
        parsed = JSON.parse(aggressiveSanitized)
        console.log('Successfully parsed after aggressive sanitization')
      } catch (retryError: any) {
        throw new Error(`Failed to parse JSON response: ${parseError.message}. The AI response may be malformed.`)
      }
    }
    
    if (!Array.isArray(parsed)) {
      console.error('Parsed JSON is not an array. Type:', typeof parsed, 'Value:', parsed)
      throw new Error('Parsed JSON is not an array. The AI may have returned a single object instead of an array.')
    }
    
    if (parsed.length === 0) {
      console.error('Parsed array is empty')
      throw new Error('The AI returned an empty array. No questions were generated.')
    }
    
    // Validate and fix questions
    const validatedQuestions = []
    // First, collect all valid questions from the parsed response
    for (let idx = 0; idx < parsed.length; idx++) {
      const question = parsed[idx]
      
      if (!question.question) {
        console.warn(`Question ${idx + 1}: Missing question text`)
        continue
      }
      
      if (!question.options || !Array.isArray(question.options)) {
        console.warn(`Question ${idx + 1}: Missing or invalid options array. Received:`, question.options)
        continue
      }
      
      // Log original options for debugging
      if (question.options.length === 0 || question.options.some((opt: any) => !opt || !opt.text || opt.text.trim() === '')) {
        console.warn(`Question ${idx + 1}: Options are empty or invalid. Original options:`, JSON.stringify(question.options))
      }
      
      // Ensure correct number of options - CRITICAL: Always trim to numOptions first
      let options = Array.isArray(question.options) ? question.options : []
      
      // Log original count for debugging
      const originalOptionCount = options.length
      if (originalOptionCount !== numOptions) {
        console.warn(`Question ${idx + 1}: Received ${originalOptionCount} options, expected ${numOptions}`)
      }
      
      // CRITICAL: FORCE trim to numOptions BEFORE processing to prevent overflow
      // This is the most important safeguard - always enforce exact count
      if (options.length > numOptions) {
        console.warn(`Question ${idx + 1}: FORCE TRIMMING ${options.length} options down to ${numOptions}`)
          options = options.slice(0, numOptions)
      } else if (options.length < numOptions) {
        console.warn(`Question ${idx + 1}: Only ${options.length} options provided, expected ${numOptions}`)
      }
      
      // DOUBLE-CHECK: Ensure options array is exactly numOptions length
      if (options.length !== numOptions) {
        console.error(`Question ${idx + 1}: ERROR - After trimming, options.length (${options.length}) != numOptions (${numOptions}). Force correcting.`)
        if (options.length > numOptions) {
          options = options.slice(0, numOptions)
        }
      }
      
      // Validate options - filter out empty or invalid ones
      const validOptions = []
      let hasCorrectAnswer = false
      
      // CRITICAL: Only process exactly numOptions to prevent any overflow
      // Use numOptions directly since we've already trimmed
      const maxOptionsToProcess = Math.min(options.length, numOptions)
      if (maxOptionsToProcess > numOptions) {
        console.error(`Question ${idx + 1}: ERROR - maxOptionsToProcess (${maxOptionsToProcess}) > numOptions (${numOptions}). Using numOptions.`)
      }
      for (let optIdx = 0; optIdx < maxOptionsToProcess; optIdx++) {
        // HARD STOP: If we already have numOptions valid options, stop processing
        if (validOptions.length >= numOptions) {
          console.warn(`Question ${idx + 1}: Already have ${validOptions.length} valid options (target: ${numOptions}), stopping validation loop early.`)
          break
        }
        
        const option = options[optIdx]
        // Skip options without text or with empty/placeholder text
        if (!option || !option.text || typeof option.text !== 'string') {
          console.warn(`Question ${idx + 1}: Skipping invalid option:`, option)
          continue
        }
        
        const optionText = option.text.trim()
        
        // Skip placeholder text like "Option A", "Option B", etc., but allow short valid answers
        if (optionText.match(/^Option\s+[A-Z]$/i) || optionText === '') {
          console.warn(`Question ${idx + 1}: Skipping placeholder or empty option: "${optionText}"`)
          continue
        }
        
        // Allow very short answers (like single digits, fractions, etc.) but log them
        if (optionText.length < 1) {
          console.warn(`Question ${idx + 1}: Skipping empty option`)
          continue
        }
        
        // Determine logic - check for correct answer markers
        let optionLogic = option.logic || 'Plausible distractor'
        const logicUpper = String(optionLogic).toUpperCase().trim()
        
        // Check if this is marked as correct answer
        // Only accept explicit CA markers - don't auto-assume first option is correct
        const isCorrectAnswer = logicUpper === 'CA' || 
                                logicUpper === 'CORRECT' ||
                                logicUpper === 'CORRECT ANSWER' ||
                                (logicUpper.includes('CORRECT') && !logicUpper.includes('INCORRECT')) ||
                                (logicUpper.includes('RIGHT') && !logicUpper.includes('WRONG'))
        
        if (isCorrectAnswer && !hasCorrectAnswer) {
          optionLogic = 'CA'
            hasCorrectAnswer = true
        } else if (isCorrectAnswer && hasCorrectAnswer) {
          // Multiple correct answers - mark this as distractor
          optionLogic = 'Plausible distractor'
        } else if (!option.logic) {
          // No logic provided - default to distractor
          optionLogic = 'Plausible distractor'
          } else {
          // Keep original logic
          optionLogic = option.logic
        }
        
        validOptions.push({
          text: optionText,
          logic: optionLogic
        })
        
        // HARD STOP: If we've reached numOptions, stop immediately
        if (validOptions.length >= numOptions) {
          break
        }
      }
      
      // CRITICAL SAFEGUARD: Immediately trim validOptions if it somehow exceeds numOptions
      if (validOptions.length > numOptions) {
        console.error(`Question ${idx + 1}: ERROR - validOptions has ${validOptions.length} items after validation loop, but numOptions is ${numOptions}. Force trimming immediately.`)
        validOptions.splice(numOptions, validOptions.length - numOptions) // Remove all items beyond numOptions
      }
      
      // If no valid options were found, log error and skip this question
      if (validOptions.length === 0) {
        console.error(`Question ${idx + 1}: No valid options found after validation. Original options:`, JSON.stringify(question.options))
        continue
      }
      
      // If no correct answer found, log error and mark first option as CA (with warning)
      if (!hasCorrectAnswer && validOptions.length > 0) {
        console.error(`Question ${idx + 1}: WARNING - No correct answer (CA) found in options. Marking first option as CA. This may be incorrect! Original options:`, JSON.stringify(question.options))
        console.warn(`Question ${idx + 1}: First option "${validOptions[0].text}" is being marked as CA, but this was not verified as correct by the AI.`)
        validOptions[0].logic = 'CA'
      }
      
      // Validate that the solution mentions the correct answer (if solution exists)
      if (question.solution && validOptions.length > 0) {
        const correctOption = validOptions.find(opt => opt.logic === 'CA')
        if (correctOption) {
          const solutionText = question.solution.toLowerCase()
          const correctAnswerText = correctOption.text.toLowerCase().trim()
          // Check if solution contains the correct answer (allowing for formatting differences)
          const answerInSolution = solutionText.includes(correctAnswerText) || 
                                   solutionText.includes(correctAnswerText.replace(/\s+/g, '')) ||
                                   // Check for common variations (fractions, decimals, etc.)
                                   (correctAnswerText.match(/\d+/) && solutionText.match(new RegExp(correctAnswerText.match(/\d+/)?.[0] || '')))
          
          if (!answerInSolution && correctAnswerText.length > 0) {
            console.warn(`Question ${idx + 1}: WARNING - Solution may not match the marked correct answer "${correctOption.text}". Please verify manually.`)
            console.warn(`Question ${idx + 1}: Solution preview: ${question.solution.substring(0, 100)}...`)
          }
        }
      }
      
      // If we don't have enough valid options, pad with placeholders as last resort
      // This should rarely happen if GPT generates properly, but we need to ensure we have the right number
      if (validOptions.length < numOptions) {
        console.error(`Question ${idx + 1}: Only ${validOptions.length} valid options found, expected ${numOptions}. Padding with placeholders.`)
        // Only add placeholders if we have at least one valid option
        // This indicates GPT partially generated options but not enough
      while (validOptions.length < numOptions) {
        validOptions.push({
          text: `Option ${String.fromCharCode(65 + validOptions.length)}`,
          logic: 'Plausible distractor'
        })
        }
      }
      
      // CRITICAL: Always trim to exact number needed - this is a final safeguard
      let finalOptions = validOptions.slice(0, numOptions)
      
      // Additional safeguard: Log and force trim if somehow we still have more
      if (finalOptions.length > numOptions) {
        console.error(`Question ${idx + 1}: ERROR - finalOptions has ${finalOptions.length} items but numOptions is ${numOptions}. Force trimming.`)
        finalOptions = finalOptions.slice(0, numOptions)
      }
      
      // Final validation: Ensure we have exactly numOptions
      if (finalOptions.length !== numOptions) {
        console.error(`Question ${idx + 1}: WARNING - finalOptions has ${finalOptions.length} items, expected ${numOptions}`)
      }
      
      // Store image description (not generating actual images)
      const imageDescription = question.image || ''
      
      validatedQuestions.push({
        question: String(question.question).trim(),
        options: finalOptions,
        image: imageDescription, // This is now an image description, not a URL
        solution: question.solution ? String(question.solution).trim() : ''
      })
    }
    
    if (validatedQuestions.length === 0) {
      // Log the raw response for debugging
      console.error('No valid questions were generated. Parsed response:', JSON.stringify(parsed, null, 2))
      console.error('Original content length:', content?.length || 0)
      throw new Error('No valid questions were generated. Please check the base question format and try again. If the issue persists, the generated questions may not match the required format.')
    }
    
    // Ensure we have exactly the requested number of questions
    if (validatedQuestions.length < numQuestions) {
      console.warn(`Only ${validatedQuestions.length} valid questions generated, but ${numQuestions} requested. Parsed response had ${parsed.length} questions.`)
      throw new Error(`Only ${validatedQuestions.length} valid question(s) were generated, but ${numQuestions} were requested. Please try again or check the base question format.`)
    }
    
    // If we have more than requested, trim to exact number
    if (validatedQuestions.length > numQuestions) {
      console.warn(`Generated ${validatedQuestions.length} questions, but only ${numQuestions} requested. Trimming to requested number.`)
    return validatedQuestions.slice(0, numQuestions)
    }
    
    // Return exactly the requested number
    return validatedQuestions
  } catch (error: any) {
    if (error instanceof SyntaxError) {
      throw new Error(`Failed to parse GPT response as JSON: ${error.message}`)
    }
    throw error
  }
}

