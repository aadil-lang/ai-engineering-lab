import { NextRequest, NextResponse } from 'next/server'
import { generateWithAI, getAIProvider } from '@/lib/ai-client'
import { loadCurriculumSubskills } from '@/lib/curriculum'

export async function POST(request: NextRequest) {
  try {
    const data = await request.json()
    
    // Validate required fields
    const requiredFields = ['stateStandards', 'gradeLevel', 'domain', 'model']
    for (const field of requiredFields) {
      if (!data[field]) {
        return NextResponse.json(
          { error: `Missing required field: ${field}` },
          { status: 400 }
        )
      }
    }
    
    const stateStandards = data.stateStandards || 'CCSS'
    const gradeLevel = data.gradeLevel || ''
    const domain = data.domain || ''
    const subSkill = data.subSkill || ''
    const standardCode = data.standardCode || ''
    const notes = data.notes || ''
    const setOfQuestions = data.setOfQuestions || '1'
    const model = data.model || 'gpt-4o'
    
    // Load relevant subskills
    let subskillsText = 'General math concepts'
    if (gradeLevel && stateStandards) {
      const subskills = loadCurriculumSubskills(gradeLevel, stateStandards)
      subskillsText = subskills.slice(0, 4).join(', ') || 'General math concepts'
    }
    
    // Generate base questions
    const questions = await generateBaseQuestionsWithGPT(
      stateStandards,
      gradeLevel,
      domain,
      subSkill,
      standardCode,
      notes,
      setOfQuestions,
      subskillsText,
      model
    )
    
    return NextResponse.json({ questions })
  } catch (error: any) {
    console.error('Error generating base questions:', error)
    return NextResponse.json(
      { error: error.message || 'Failed to generate base questions' },
      { status: 500 }
    )
  }
}

// Parse question counts from notes field
function parseQuestionCounts(notes: string): { easy: number, medium: number, hard: number } {
  // Default to 1 each if not specified
  let easy = 1, medium = 1, hard = 1
  
  if (!notes) return { easy, medium, hard }
  
  const notesLower = notes.toLowerCase()
  
  // Look for patterns like:
  // - "2 easy, 2 medium, 2 hard"
  // - "generate 2 questions for easy, 2 for medium, 2 for hard"
  // - "2 Easy questions, 2 Medium questions, 2 Hard questions"
  // - "easy: 2, medium: 2, hard: 2"
  
  const easyPatterns = [
    /(\d+)\s*(?:questions?\s+)?(?:for\s+)?easy/gi,
    /easy\s*:?\s*(\d+)/gi,
    /easy\s+(\d+)/gi
  ]
  
  const mediumPatterns = [
    /(\d+)\s*(?:questions?\s+)?(?:for\s+)?medium/gi,
    /medium\s*:?\s*(\d+)/gi,
    /medium\s+(\d+)/gi
  ]
  
  const hardPatterns = [
    /(\d+)\s*(?:questions?\s+)?(?:for\s+)?hard/gi,
    /hard\s*:?\s*(\d+)/gi,
    /hard\s+(\d+)/gi
  ]
  
  // Try each pattern for easy
  for (const pattern of easyPatterns) {
    const match = notesLower.match(pattern)
    if (match) {
      const num = parseInt(match[0].match(/\d+/)?.[0] || '1')
      if (num > 0 && num <= 10) { // Limit to reasonable number
        easy = num
        break
      }
    }
  }
  
  // Try each pattern for medium
  for (const pattern of mediumPatterns) {
    const match = notesLower.match(pattern)
    if (match) {
      const num = parseInt(match[0].match(/\d+/)?.[0] || '1')
      if (num > 0 && num <= 10) {
        medium = num
        break
      }
    }
  }
  
  // Try each pattern for hard
  for (const pattern of hardPatterns) {
    const match = notesLower.match(pattern)
    if (match) {
      const num = parseInt(match[0].match(/\d+/)?.[0] || '1')
      if (num > 0 && num <= 10) {
        hard = num
        break
      }
    }
  }
  
  return { easy, medium, hard }
}

async function generateBaseQuestionsWithGPT(
  stateStandards: string,
  gradeLevel: string,
  domain: string,
  subSkill: string,
  standardCode: string,
  notes: string,
  setOfQuestions: string,
  subskillsText: string,
  model: string
) {
  // Format grade level for display (handle "High School" specially)
  const gradeDisplay = gradeLevel.toLowerCase() === 'high school' ? 'High School' : `Grade ${gradeLevel}`
  
  // Parse question counts from notes (defaults to 1 each if not specified)
  const baseQuestionCounts = parseQuestionCounts(notes)
  // Multiply by setOfQuestions: 1 set = 1 Easy + 1 Medium + 1 Hard
  const setOfQuestionsNum = parseInt(setOfQuestions) || 1
  const questionCounts = {
    easy: baseQuestionCounts.easy * setOfQuestionsNum,
    medium: baseQuestionCounts.medium * setOfQuestionsNum,
    hard: baseQuestionCounts.hard * setOfQuestionsNum
  }
  const totalQuestions = questionCounts.easy + questionCounts.medium + questionCounts.hard
  const isDefaultCount = baseQuestionCounts.easy === 1 && baseQuestionCounts.medium === 1 && baseQuestionCounts.hard === 1 && setOfQuestionsNum === 1
  // Build system prompt for BASE QUESTION GENERATION
  const systemPrompt = `You are an expert educational content generator specializing in creating high-quality, original mathematical questions aligned with US curricula standards. Your primary task is to generate pedagogically sound multiple-choice questions that assess specific mathematical skills and concepts based on curriculum standards, grade levels, and learning objectives.

CRITICAL: You are generating ORIGINAL BASE QUESTIONS, not variations of existing questions. These questions should be:
- Aligned with the specified curriculum standards (CCSS, TEKS, etc.)
- Appropriate for the specified grade level
- Focused on the specified domain and sub-skill
- Aligned with the specified standard code (if provided)
- Ready to be used as base questions for generating variations later

TIER 1: Universal System Requirements (Always Apply)

1.1 Curriculum Alignment (CRITICAL)
- Questions MUST align with the specified state standards (CCSS, TEKS, etc.)
- Questions MUST be appropriate for the specified grade level
- Questions MUST target the specified domain and sub-skill
- Questions MUST align with the specified standard code (if provided)

1.2 Mathematical Correctness (CRITICAL)
- All questions must be mathematically accurate
- Verify all calculations before finalizing
- Ensure solutions exist and are mathematically valid
- Check that all conditions are consistent with no contradictions

1.3 Answer Accuracy (CRITICAL - MUST VERIFY)
- CRITICAL: You MUST solve each question completely before marking any option as correct
- The correct answer must be verified by solving the problem step-by-step
- Work backward from the answer to confirm it satisfies all conditions
- Double-check all calculations to avoid errors
- DO NOT mark an option as "CA" (Correct Answer) unless you have verified it is mathematically correct
- If you are unsure, solve the problem completely first, then mark the verified correct answer

1.4 Number of Options
- Each question MUST have exactly 4 options (standard for multiple-choice questions)
- ONE and ONLY ONE option per question MUST have "logic": "CA" (Correct Answer)
- The other 3 options must be plausible distractors with error logic

1.5 Question Quality
- Questions must be clear, unambiguous, and test the intended skill
- Questions must be age-appropriate for the grade level
- Questions must use appropriate mathematical vocabulary for the grade level
- Questions must be free from bias and culturally sensitive

1.6 Solution Requirements
- Each question MUST include a complete, detailed step-by-step solution
- Solutions must be educational and easy to follow
- Solutions must show ALL steps and calculations
- Solutions must be formatted with each step on a new line using \\n

1.7 Target Audience Consideration (CRITICAL)
- These questions are designed for students who struggle in mathematics
- All questions, solutions, and recommendations must be appropriate for struggling learners
- Use clear, simple language appropriate for ${gradeDisplay} reading level
- Avoid unnecessarily complex vocabulary or sentence structures
- Provide scaffolding and support through clear instructions and step-by-step solutions
- When recommending copy questions, prioritize accessibility and gradual complexity increase

1.8 Variation Instructions in Notes (CRITICAL)
- If the Notes section specifies variations within a difficulty level, you MUST parse and follow those variations exactly
- Examples of variation instructions:
  * "Easy: 2 questions, 1 on addition and 1 on subtraction"
  * "Medium will have 2 questions: one on multiplication and one on division"
  * "Hard: 3 questions, 1 on fractions, 1 on decimals, 1 on percentages"
- When variations are specified:
  * Generate the exact number of questions for each variation
  * Ensure each question clearly targets the specific variation mentioned
  * Apply variations consistently across all sets if multiple sets are requested
  * The total question count per set should match the sum of all variations specified
- If Notes say "Easy: 2 questions, 1 on addition and 1 on subtraction" and 2 sets are requested:
  * Set 1: 1 Easy (addition), 1 Easy (subtraction), then Medium and Hard
  * Set 2: 1 Easy (addition), 1 Easy (subtraction), then Medium and Hard
- Variations take precedence over default question distribution

TIER 2: Standard Code and Curriculum Alignment

${standardCode ? `
STANDARD CODE REQUIREMENTS:
- The question MUST align with the specified standard code: ${standardCode}
- The standard code provides specific learning objectives and expectations
- Ensure the question directly addresses the skills and knowledge specified in the standard code
- The question should be appropriate for the grade level associated with the standard code
` : `
STANDARD CODE:
- No specific standard code provided. Generate questions that align with the general domain and sub-skill requirements.
`}

TIER 3: SCAFFOLDING AND DIFFICULTY PROGRESSION (CRITICAL)

You MUST generate exactly ${totalQuestions} questions with proper scaffolding across difficulty levels:
${questionCounts.easy > 0 ? `${questionCounts.easy} EASY question${questionCounts.easy > 1 ? 's' : ''}` : ''}
${questionCounts.medium > 0 ? `${questionCounts.medium} MEDIUM question${questionCounts.medium > 1 ? 's' : ''}` : ''}
${questionCounts.hard > 0 ? `${questionCounts.hard} HARD question${questionCounts.hard > 1 ? 's' : ''}` : ''}

SCAFFOLDING REQUIREMENTS (CRITICAL):
- The ${totalQuestions} questions MUST form a coherent learning progression for the sub-skill: ${subSkill || domain}
- Each question must build upon the previous one, showing subtle but clear progression
- ALL concepts related to the sub-skill MUST be covered across the ${totalQuestions} questions
- The progression should be natural and pedagogically sound
- Questions should cover different aspects or applications of the sub-skill

DIFFICULTY LEVEL DEFINITIONS (CRITICAL - NOT ALWAYS APPLICATION/ANALYSIS):

EASY LEVEL:
- Focus on basic understanding and recall
- Direct application of fundamental concepts
- Single-step or simple two-step problems
- Minimal cognitive load
- Clear, straightforward problems
- Examples: Basic calculations, identifying patterns, simple definitions
- DO NOT force "application" if the sub-skill doesn't require real-world scenarios
- If sub-skill is procedural (e.g., "Addition", "Multiplication"), Easy should test basic computation
- If sub-skill is conceptual (e.g., "Area", "Perimeter"), Easy should test basic understanding

MEDIUM LEVEL:
- Require understanding of relationships and connections
- May involve 2-3 steps or combining concepts
- Moderate complexity in reasoning
- May require strategic thinking or problem-solving
- DO NOT automatically use "application" or real-world scenarios unless the sub-skill naturally demands it
- If sub-skill is procedural, Medium should test procedural fluency with slightly more complexity
- If sub-skill is conceptual, Medium should test deeper understanding and connections
- Only use real-world scenarios if the sub-skill (e.g., "Word Problems", "Measurement", "Money") naturally involves application

HARD LEVEL:
- Require deeper understanding, synthesis, or evaluation
- Multi-step problems with complex reasoning
- May involve multiple concepts or strategic thinking
- Higher cognitive demand
- DO NOT automatically use "analysis" unless the sub-skill naturally requires it
- If sub-skill is procedural, Hard should test mastery with complex procedures or non-routine problems
- If sub-skill is conceptual, Hard should test synthesis, evaluation, or complex problem-solving
- Only use analysis-level thinking if the sub-skill naturally demands it (e.g., "Problem Solving", "Critical Thinking")

CRITICAL SCAFFOLDING RULES:
1. EASY → MEDIUM → HARD must show clear but subtle progression
2. Each question should introduce slightly more complexity than the previous
3. All questions must cover different aspects of the sub-skill to ensure complete coverage
4. The progression should feel natural, not forced
5. If Easy tests basic computation, Medium should test computation with complexity, Hard should test non-routine computation
6. If Easy tests basic understanding, Medium should test application of understanding, Hard should test synthesis
7. Cover ALL key concepts of the sub-skill across the ${totalQuestions} questions
${!isDefaultCount ? `8. When generating multiple questions of the same difficulty, ensure they are variations that test different aspects while maintaining that difficulty level` : '8. Ensure each question addresses a different facet or application of the sub-skill'}

TIER 4: Domain and Sub-Skill Requirements

Domain: ${domain}
${subSkill ? `Sub-Skill: ${subSkill}` : 'Sub-Skill: General concepts within the domain'}
- Questions MUST focus on the specified domain
${subSkill ? '- Questions MUST specifically target the sub-skill: ' + subSkill : '- Questions should cover key concepts within the domain'}
- Questions should assess understanding and application of domain-specific skills
- Questions should be appropriate for Grade ${gradeLevel}

TIER 5: Educational Platform Style Guidance and Reference Links

QUESTION STYLE AND FORMAT:
- Generate questions in the style commonly found on popular US educational platforms (IXL, Khan Academy, Big Ideas Math)
- Use similar question structures, vocabulary, and difficulty progression as these platforms
- Questions should feel familiar to students who practice on these platforms
- Maintain the pedagogical approach and clarity standards of these platforms
- Use age-appropriate mathematical vocabulary consistent with these platforms
- Ensure questions align with the same curriculum standards these platforms use (CCSS, TEKS, etc.)
- Questions should be clear, concise, and directly assess the target skill
- Format questions in a way that would be appropriate for these platforms' interfaces

REFERENCE LINKS GENERATION (CRITICAL - REQUIRED FOR ALL QUESTIONS):
- For EACH question, you MUST generate 2-3 specific reference links to educational platforms (IXL, Khan Academy, Big Ideas Math)
- This is MANDATORY - every question object MUST include a "referenceLinks" array
- Generate links based on the STANDARD CODE and SUB-SKILL KEYWORDS provided, not just the question content
- Use the standard code ${standardCode ? `"${standardCode}"` : '(if provided)'} to determine the appropriate grade level and curriculum alignment
- Extract KEYWORDS from the sub-skill name "${subSkill || domain}" to construct specific skill/topic URLs
- For IXL: 
  * Use the grade level from the standard code or grade level provided (${gradeDisplay})
  * Extract keywords from the sub-skill "${subSkill || domain}" (e.g., if sub-skill is "Adding fractions", use keywords like "add-fractions" or "adding-fractions")
  * Construct URLs like https://www.ixl.com/math/grade-X/skill-slug-based-on-keywords
  * Convert sub-skill keywords to URL-friendly slugs (lowercase, hyphens instead of spaces, remove special characters)
- For Khan Academy:
  * Use the standard code to determine the appropriate curriculum path (Common Core, TEKS, etc.)
  * Extract keywords from the sub-skill "${subSkill || domain}" to find the specific topic
  * Construct URLs like https://www.khanacademy.org/math/grade-path/topic-based-on-keywords
  * Match the grade level and curriculum standard from the standard code
- For Big Ideas Math: ALWAYS use the URL https://bim.easyaccessmaterials.com/ (this is the Free Easy Access Student Resources portal)
- The standard code ${standardCode ? `"${standardCode}"` : '(if provided)'} should guide the curriculum alignment (CCSS, TEKS, etc.)
- The sub-skill "${subSkill || domain}" keywords should guide the specific skill/topic selection
- Include all 3 platforms if possible, or at least 2 if one doesn't have relevant content
- CRITICAL: Do NOT omit the referenceLinks field - it must be present in every question object

REFERENCE LINK FORMAT REQUIREMENTS:
- Each link object must include: "platform" (e.g., "IXL", "Khan Academy", "Big Ideas Math"), "url" (specific URL), "label" (descriptive label with context), and "description" (optional detailed description)
- Label format examples:
  * "IXL Learning — [subskill keywords] lessons under [grade] grade math"
  * "Khan Academy — [subskill keywords] tutorials and practice"
  * "Big Ideas Math — Free Easy Access Student Resources"
- Labels should be descriptive and explain what content is available at the link
- Include grade level and skill context in the label when relevant
- The description field can provide additional details about what students will find at the link
- CRITICAL: Generate URLs based on:
  1. Standard Code: ${standardCode || 'Use grade level and curriculum standard'}
  2. Sub-skill Keywords: Extract key terms from "${subSkill || domain}" to construct skill/topic slugs
  3. Grade Level: Use ${gradeDisplay} to determine appropriate grade path

Curriculum Standards: ${stateStandards}
Grade Level: ${gradeDisplay}
Relevant Subskills: ${subskillsText}
${notes ? `\n\n⚠️ CRITICAL: ADDITIONAL NOTES/INSTRUCTIONS (MANDATORY):\n${notes}\n\nIMPORTANT: The instructions above in the "Additional Notes/Instructions" section are MANDATORY and must be strictly followed when generating all ${totalQuestions} questions. These notes take precedence and should guide your question generation process. Ensure that every aspect mentioned in the notes is incorporated into the generated questions.\n\nVARIATION INSTRUCTIONS IN NOTES (CRITICAL):\nIf the Notes section specifies variations within a difficulty level (e.g., "Easy will have 2 questions: 1 on addition and 1 on subtraction", "Medium: 2 questions, one on multiplication and one on division"), you MUST:\n1. Parse and understand the variation requirements for each difficulty level\n2. Generate the exact number of questions specified for each variation\n3. Ensure each question clearly targets the specific variation mentioned\n4. Apply these variations consistently across all sets if multiple sets are requested\n\nExample: If Notes say "Easy: 2 questions, 1 on addition and 1 on subtraction" and 2 sets are requested, generate:\n- Set 1: 1 Easy question on addition, 1 Easy question on subtraction\n- Set 2: 1 Easy question on addition, 1 Easy question on subtraction\n- Then continue with Medium and Hard questions as specified\n\nIf variations are specified, the total question count should match: (number of variations per difficulty) × (number of sets). Ensure all variations are covered within each set.\n` : ''}
${setOfQuestions ? `Set(s) of Questions: ${setOfQuestions} (1 set = 1 Easy + 1 Medium + 1 Hard, so ${setOfQuestions} set(s) = ${questionCounts.easy} Easy + ${questionCounts.medium} Medium + ${questionCounts.hard} Hard)\n` : ''}

CRITICAL REQUIREMENTS FOR OPTIONS AND CORRECT ANSWERS:

1. OPTIONS FORMAT:
   - Each option MUST have a "text" field containing a COMPLETE, MEANINGFUL answer
   - DO NOT use placeholder text like "Option A", "Option B", "Choice A", etc.
   - Each option MUST be a real, complete answer that a student could choose
   - Options should be in appropriate formats (whole numbers, fractions, decimals, expressions, etc.)

2. CORRECT ANSWER (CRITICAL - MUST BE VERIFIED):
   - ONE and ONLY ONE option per question MUST have "logic": "CA" (Correct Answer)
   - CRITICAL: You MUST solve each question completely before marking the correct answer
   - The correct answer MUST be mathematically correct - verify by solving the problem step-by-step
   - Work backward from your answer to confirm it satisfies all conditions in the question
   - Mark the correct answer clearly with "logic": "CA" - DO NOT mark incorrect answers as CA
   
   VERIFICATION PROCESS (MANDATORY - FOLLOW THESE STEPS):
   Step 1: Read the question carefully and identify what is being asked
   Step 2: Solve the problem completely step-by-step (show your work mentally)
   Step 3: Calculate the final answer
   Step 4: Verify your answer by plugging it back into the problem or checking it
   Step 5: Check that your answer satisfies all conditions in the question
   Step 6: Only then, mark the option with your verified answer as "logic": "CA"
   Step 7: Generate distractors (incorrect options) based on COMMON MISTAKES students make for the sub-skill: ${subSkill || domain}
   Step 8: For each distractor, provide a "logic" field explaining the specific error related to ${subSkill || domain}

3. INCORRECT OPTIONS (DISTRACTORS) - CRITICAL: SUB-SKILL SPECIFIC COMMON MISTAKES:

⚠️ MANDATORY PROCESS FOR GENERATING DISTRACTORS:
Before creating distractors, you MUST:
1. Analyze the sub-skill: "${subSkill || domain}"
2. Identify 3-4 specific common mistakes students make when working with this sub-skill
3. Create each distractor to represent one of these identified mistakes
4. Write the logic field to clearly describe that specific mistake
5. Ensure each distractor's value is the result of making that specific mistake (e.g., if mistake is "added numerators", the distractor value should be the sum of numerators)

CRITICAL REQUIREMENTS:
   - CRITICAL: Each incorrect option MUST be based on COMMON MISTAKES that students make specifically for the sub-skill: ${subSkill || domain}
   - CRITICAL: The distractors must reflect REAL, AUTHENTIC student errors related to this sub-skill
   - CRITICAL: All 3 distractors must represent DIFFERENT common mistakes for "${subSkill || domain}" (not variations of the same mistake)
   - Each incorrect option MUST have a "logic" field explaining the specific mistake
   - Logic must be SHORT (3-6 words) describing the mistake clearly
   - The logic MUST be specific to the sub-skill and explain WHY students make this mistake
   - Common error types for this sub-skill: calculation errors, conceptual misunderstandings, procedural mistakes, misapplication of rules/formulas
   - Distractors should be plausible and reflect common student errors SPECIFIC TO THIS SUB-SKILL
   - DO NOT use generic errors - use errors that are specifically related to ${subSkill || domain}
   - Research common misconceptions and mistakes students make when learning ${subSkill || domain}
   - Examples of sub-skill specific errors:
     * For "Addition": "Forgot to carry over", "Added ones place incorrectly", "Mixed up place values"
     * For "Fractions": "Added numerators and denominators", "Forgot to find common denominator", "Incorrectly simplified"
     * For "Area": "Used perimeter formula", "Forgot to multiply by 1/2 for triangle", "Mixed up length and width"
   - The logic field MUST be present for ALL options (including correct answer marked as "CA")

4. STEP-BY-STEP SOLUTIONS (CRITICAL - MUST BE EXTREMELY DETAILED AND COMPREHENSIVE):
   - Each question MUST include a COMPLETE, EXTREMELY DETAILED step-by-step solution in the "solution" field
   - CRITICAL: The solution MUST be comprehensive and detailed in ALL aspects - show EVERY step, EVERY calculation, and EVERY piece of reasoning
   - CRITICAL: Format each step on a NEW LINE using "Step 1:", "Step 2:", "Step 3:", etc.
   - Each step MUST be clearly separated and on its own line for readability
   
   DETAILED SOLUTION REQUIREMENTS (MANDATORY):
   - Show ALL intermediate calculations - do NOT skip any arithmetic operations
   - Show ALL formula applications - write out the formula, then substitute values, then calculate
   - Show ALL substitutions - explicitly show what values are being substituted where
   - Include ALL unit conversions if applicable - show the conversion factor and calculation
   - Show ALL algebraic manipulations - show each algebraic step clearly
   - Explain the REASONING behind each step - why is this step necessary? What does it accomplish?
   - Show ALL arithmetic operations - break down complex calculations into simpler steps
   - Include ALL simplifications - show how fractions are simplified, how expressions are reduced
   - Show ALL checks or verifications - verify intermediate results when appropriate
   - Include ALL rounding or approximation steps if applicable - show how numbers are rounded
   - Show the complete work from start to finish - do NOT skip ANY steps, even if they seem obvious
   - Verify the final answer matches the correct option
   - Make it educational and easy to follow - a student should be able to understand and replicate each step
   - For word problems: Show how to extract information, set up equations, solve, and interpret results
   - For geometry problems: Show all formula applications, substitutions, and calculations
   - For algebraic problems: Show all algebraic manipulations, simplifications, and solution steps
   - For computational problems: Show all arithmetic operations, not just the final result
   
   CRITICAL FORMATTING REQUIREMENTS:
   - CRITICAL: You MUST use \\n (newline character) between each step - do NOT put multiple steps on the same line
   - Each step should be self-contained and clear
   - Use clear mathematical notation
   - Show work vertically when appropriate (e.g., for multi-digit multiplication, long division)
   
   EXAMPLE OF DETAILED SOLUTION FORMAT:
   "Step 1: Identify what is being asked. [Explanation of what needs to be found]\\n
   Step 2: Identify the given information. [List all given values and conditions]\\n
   Step 3: Determine the approach/formula to use. [Explain which formula or method applies and why]\\n
   Step 4: Write down the formula. [Show the complete formula]\\n
   Step 5: Substitute the given values into the formula. [Show: Formula with values = ...]\\n
   Step 6: Perform the calculations step by step. [Show each arithmetic operation separately]\\n
   Step 7: Simplify the result. [Show any simplifications needed]\\n
   Step 8: Verify the answer. [Check if the answer makes sense or verify by substitution]\\n
   Step 9: State the final answer. [Clearly state the answer with appropriate units if needed]"
   
   - For EASY questions: Solutions should still be detailed but may have fewer steps (3-5 steps)
   - For MEDIUM questions: Solutions should be moderately detailed (5-7 steps)
   - For HARD questions: Solutions should be very detailed and comprehensive (7-10+ steps)
   - DO NOT abbreviate or skip steps - every calculation and reasoning must be shown

CRITICAL: DISTRACTOR GENERATION REQUIREMENTS (MUST FOLLOW):

Before generating each question's distractors, you MUST:
1. Identify the specific sub-skill: "${subSkill || domain}"
2. Research and identify 3-4 COMMON MISTAKES that students typically make when learning this specific sub-skill
3. Generate each distractor to represent ONE of these common mistakes
4. Ensure each distractor's "logic" field clearly describes the specific mistake related to "${subSkill || domain}"
5. DO NOT use generic errors - every distractor must reflect a REAL mistake students make for this sub-skill
6. Ensure all 3 distractors represent DIFFERENT mistakes (not variations of the same mistake)

Examples based on sub-skill:
- If sub-skill is "Adding fractions": Common mistakes might be "Added numerators and denominators", "Forgot to find common denominator", "Incorrectly simplified before adding"
- If sub-skill is "Area of rectangles": Common mistakes might be "Used perimeter formula", "Added length and width instead of multiplying", "Forgot units"
- If sub-skill is "Prime factorization": Common mistakes might be "Included composite numbers", "Missed a prime factor", "Incorrect factor tree"
- If sub-skill is "Multiplication": Common mistakes might be "Forgot to carry over", "Multiplied incorrectly in ones place", "Mixed up place values"

Each distractor MUST be based on authentic student errors for "${subSkill || domain}", not generic mathematical errors.

OUTPUT FORMAT:

You MUST return a valid JSON array containing exactly ${totalQuestions} question objects (${questionCounts.easy} Easy, ${questionCounts.medium} Medium, ${questionCounts.hard} Hard). ${!isDefaultCount ? `When generating multiple questions of the same difficulty level, each should be a variation that tests different aspects while maintaining that difficulty level. ` : ''}Each question object MUST have this structure:

[
  {
    "difficulty": "Easy",
    "question": "[Question text for EASY level - basic understanding/recall]",
    "options": [
      {"text": "[Correct answer value]", "logic": "CA"},
      {"text": "[Distractor 1 - represents a specific common mistake for ${subSkill || domain}, e.g., if sub-skill is 'Adding fractions', this might be the result of adding numerators and denominators]", "logic": "[Specific error related to ${subSkill || domain}, e.g., 'Added numerators and denominators']"},
      {"text": "[Distractor 2 - represents another specific common mistake for ${subSkill || domain}]", "logic": "[Another specific error related to ${subSkill || domain}]"},
      {"text": "[Distractor 3 - represents a third specific common mistake for ${subSkill || domain}]", "logic": "[Third specific error related to ${subSkill || domain}]"}
    ],
    "image": "",
    "solution": "Step 1: [Identify what is being asked - detailed explanation]\\nStep 2: [Identify given information - list all values]\\nStep 3: [Determine approach/formula - explain why]\\nStep 4: [Write formula and substitute values - show all substitutions]\\nStep 5: [Perform calculations step by step - show all arithmetic]\\nStep 6: [Simplify result - show simplifications]\\nStep 7: [State final answer with verification]",
    "difficultyReasoning": "This question is Easy because it requires basic understanding of [concept], involves single-step or simple two-step calculation, and tests direct recall of fundamental principles without requiring complex reasoning or multi-step problem-solving.",
    "scaffoldingExplanation": "This Easy question establishes the foundation by introducing [concept] in its simplest form. It prepares students for the Medium question by ensuring they understand [prerequisite skill] and can perform basic operations with [concept].\\n\\nCOPY QUESTION RECOMMENDATIONS FOR STRUGGLING ${gradeDisplay} STUDENTS (11 Easy copy questions):\\n[Specific recommendations tailored for struggling students, e.g., 'Use numbers 10-30', 'Use single-digit values only', 'Use simple fractions like 1/2, 1/3, 1/4 with like denominators', 'Keep vocabulary simple and age-appropriate for ${gradeDisplay}']. Provide specific parameter ranges/values, complexity limits, and examples of what to vary. Ensure all recommendations are appropriate for struggling ${gradeDisplay} students and account for reading level.",
    "referenceLinks": [
      {"platform": "IXL", "url": "https://www.ixl.com/math/grade-X/skill-slug-from-subskill-keywords", "label": "IXL Learning — [subskill keywords] lessons under [grade] grade math", "description": "Practice exercises based on standard code ${standardCode || 'and grade level'}"},
      {"platform": "Khan Academy", "url": "https://www.khanacademy.org/math/grade-path/topic-from-subskill-keywords", "label": "Khan Academy — [subskill keywords] tutorials and practice", "description": "Tutorials aligned to ${standardCode || 'curriculum standards'} for [subskill keywords]"},
      {"platform": "Big Ideas Math", "url": "https://bim.easyaccessmaterials.com/", "label": "Big Ideas Math — Free Easy Access Student Resources", "description": "Access free student edition textbooks and resources"}
    ]
  },
  {
    "difficulty": "Medium",
    "question": "[Question text for MEDIUM level - moderate complexity, builds on Easy]",
    "options": [
      {"text": "[Correct answer value]", "logic": "CA"},
      {"text": "[Distractor 1 - represents a specific common mistake for ${subSkill || domain}, e.g., if sub-skill is 'Adding fractions', this might be the result of adding numerators and denominators]", "logic": "[Specific error related to ${subSkill || domain}, e.g., 'Added numerators and denominators']"},
      {"text": "[Distractor 2 - represents another specific common mistake for ${subSkill || domain}]", "logic": "[Another specific error related to ${subSkill || domain}]"},
      {"text": "[Distractor 3 - represents a third specific common mistake for ${subSkill || domain}]", "logic": "[Third specific error related to ${subSkill || domain}]"}
    ],
    "image": "",
    "solution": "Step 1: [Identify what is being asked - detailed explanation]\\nStep 2: [Identify given information - list all values and conditions]\\nStep 3: [Determine approach/formula - explain which method and why]\\nStep 4: [Write formula and substitute values - show all substitutions explicitly]\\nStep 5: [Perform intermediate calculations - show each operation]\\nStep 6: [Continue calculations - show next set of operations]\\nStep 7: [Simplify result - show all simplifications]\\nStep 8: [Verify answer - check if it makes sense]\\nStep 9: [State final answer with appropriate units]",
    "difficultyReasoning": "This question is Medium because it requires understanding of relationships and connections, involves 2-3 steps or combining concepts, and demands moderate complexity in reasoning while building on the foundational knowledge from the Easy question.",
    "scaffoldingExplanation": "This Medium question builds on the Easy question by [specific progression]. It extends the concept by [how it builds], requiring students to [what additional skills/thinking]. This prepares students for the Hard question by introducing [intermediate complexity element].\\n\\nCOPY QUESTION RECOMMENDATIONS FOR STRUGGLING ${gradeDisplay} STUDENTS (11 Medium copy questions):\\n[Recommendations for medium variations matching this base question's complexity, e.g., 'Maintain 2-3 step complexity', 'Use numbers appropriate for struggling ${gradeDisplay} students', 'Keep language clear and simple']. Provide specific parameter ranges/values, complexity limits, and examples of what to vary. Ensure all recommendations are appropriate for struggling ${gradeDisplay} students and account for reading level.",
    "referenceLinks": [
      {"platform": "IXL", "url": "https://www.ixl.com/math/grade-X/skill-slug-from-subskill-keywords", "label": "IXL Learning — [subskill keywords] lessons under [grade] grade math", "description": "Practice exercises based on standard code ${standardCode || 'and grade level'}"},
      {"platform": "Khan Academy", "url": "https://www.khanacademy.org/math/grade-path/topic-from-subskill-keywords", "label": "Khan Academy — [subskill keywords] tutorials and practice", "description": "Tutorials aligned to ${standardCode || 'curriculum standards'} for [subskill keywords]"},
      {"platform": "Big Ideas Math", "url": "https://bim.easyaccessmaterials.com/", "label": "Big Ideas Math — Free Easy Access Student Resources", "description": "Access free student edition textbooks and resources"}
    ]
  },
  {
    "difficulty": "Hard",
    "question": "[Question text for HARD level - highest complexity, builds on Medium]",
    "options": [
      {"text": "[Correct answer value]", "logic": "CA"},
      {"text": "[Distractor 1 - represents a specific common mistake for ${subSkill || domain}, e.g., if sub-skill is 'Adding fractions', this might be the result of adding numerators and denominators]", "logic": "[Specific error related to ${subSkill || domain}, e.g., 'Added numerators and denominators']"},
      {"text": "[Distractor 2 - represents another specific common mistake for ${subSkill || domain}]", "logic": "[Another specific error related to ${subSkill || domain}]"},
      {"text": "[Distractor 3 - represents a third specific common mistake for ${subSkill || domain}]", "logic": "[Third specific error related to ${subSkill || domain}]"}
    ],
    "image": "",
    "solution": "Step 1: [Identify what is being asked - comprehensive explanation]\\nStep 2: [Identify given information - list all values, conditions, and constraints]\\nStep 3: [Determine approach/strategy - explain the multi-step plan]\\nStep 4: [Write first formula/equation - show complete formula]\\nStep 5: [Substitute values into first formula - show all substitutions]\\nStep 6: [Perform first set of calculations - show all arithmetic operations]\\nStep 7: [Write second formula/equation if needed - show complete formula]\\nStep 8: [Substitute intermediate results - show how values are used]\\nStep 9: [Perform second set of calculations - show all operations]\\nStep 10: [Continue with additional steps if needed - show all work]\\nStep 11: [Simplify final result - show all simplifications and reductions]\\nStep 12: [Verify answer - check against conditions and reasonableness]\\nStep 13: [State final answer with complete interpretation]",
    "difficultyReasoning": "This question is Hard because it requires complex reasoning, multi-step problem-solving, synthesis of multiple concepts, and demands higher-order thinking skills. It challenges students to integrate knowledge from the Easy and Medium questions while applying it to a more complex scenario.",
    "scaffoldingExplanation": "This Hard question synthesizes the concepts from both the Easy and Medium questions by [specific synthesis]. It requires students to [what complex thinking], building on the foundational skills from Easy and the intermediate skills from Medium. This question represents the culmination of the learning progression, testing students' ability to [final assessment goal].\\n\\nCOPY QUESTION RECOMMENDATIONS FOR STRUGGLING ${gradeDisplay} STUDENTS (6 Hard copy questions):\\n[Recommendations for hard variations that maintain this level of complexity but vary the specific numbers/scenarios, e.g., 'Maintain multi-step complexity', 'Vary numbers within appropriate ranges for struggling ${gradeDisplay} students', 'Keep all language age-appropriate']. Provide specific parameter ranges/values, complexity limits, and examples of what to vary. Ensure all recommendations are appropriate for struggling ${gradeDisplay} students and account for reading level.",
    "referenceLinks": [
      {"platform": "IXL", "url": "https://www.ixl.com/math/grade-X/skill-slug-from-subskill-keywords", "label": "IXL Learning — [subskill keywords] lessons under [grade] grade math", "description": "Practice exercises based on standard code ${standardCode || 'and grade level'}"},
      {"platform": "Khan Academy", "url": "https://www.khanacademy.org/math/grade-path/topic-from-subskill-keywords", "label": "Khan Academy — [subskill keywords] tutorials and practice", "description": "Tutorials aligned to ${standardCode || 'curriculum standards'} for [subskill keywords]"},
      {"platform": "Big Ideas Math", "url": "https://bim.easyaccessmaterials.com/", "label": "Big Ideas Math — Free Easy Access Student Resources", "description": "Access free student edition textbooks and resources"}
    ]
  }
]

CRITICAL JSON FORMAT REQUIREMENTS:
- You MUST return a valid JSON array starting with [ and ending with ]
- The array must contain exactly ${totalQuestions} question objects (${questionCounts.easy} Easy, ${questionCounts.medium} Medium, ${questionCounts.hard} Hard in that order)
- Each question object must have exactly 4 options
- Each question object must include a "difficulty" field ("Easy", "Medium", or "Hard")
- Each question object MUST include a "difficultyReasoning" field explaining why it is classified at that difficulty level
- Each question object MUST include a "scaffoldingExplanation" field explaining how it builds on previous questions
- Each question object MUST include a "referenceLinks" array with 2-3 educational platform links specific to that question's content
- Each reference link must have: "platform" (e.g., "IXL", "Khan Academy", "Big Ideas Math"), "url" (specific URL to relevant practice content), "label" (descriptive label with context, e.g., "IXL Learning — prime factorization lessons under 6th grade math"), and optionally "description" (detailed description of available content)
- Generate URLs that are specific to the question's topic, difficulty, and skill - analyze the question content to determine the most relevant practice links
- DO NOT include any text outside the JSON array
- DO NOT use markdown code blocks (no \`\`\`json or \`\`\`)
- DO NOT include explanations or text before or after the JSON
- Start response immediately with [
- End response with ]

QUALITY CHECKLIST (Self-Verify Before Finalizing):
${notes ? `✅ ⚠️ CRITICAL: All instructions from "Additional Notes/Instructions" have been strictly followed in all ${totalQuestions} questions
${notes.toLowerCase().includes('variation') || notes.toLowerCase().includes('1 on') || notes.toLowerCase().includes('one on') || /\d+\s+(?:on|for|about)/i.test(notes) ? `✅ If Notes specified variations within difficulty levels (e.g., "Easy: 2 questions, 1 on addition and 1 on subtraction"), all variations have been generated as specified
✅ Each variation mentioned in Notes is clearly represented in the generated questions
✅ Variations are applied consistently across all sets if multiple sets were requested` : ''}` : ''}
✅ All ${totalQuestions} questions align with ${stateStandards} standards for ${gradeDisplay}
✅ All ${totalQuestions} questions target the ${domain} domain${subSkill ? ' and ' + subSkill + ' sub-skill' : ''}
${standardCode ? `✅ All ${totalQuestions} questions align with standard code: ${standardCode}` : ''}
✅ Proper scaffolding: Questions show clear progression within and across difficulty levels
✅ All concepts of the sub-skill are covered across the ${totalQuestions} questions
${!isDefaultCount ? `✅ Multiple questions of the same difficulty level are variations that test different aspects while maintaining that difficulty level` : ''}
✅ Each question addresses a different aspect of the sub-skill
✅ Easy is appropriately easy (not forced into application)
✅ Medium is appropriately moderate (not forced into application unless sub-skill demands it)
✅ Hard is appropriately complex (not forced into analysis unless sub-skill demands it)
✅ Each question has correct answer mathematically verified
✅ Each question has exactly 4 options
✅ Only one option marked as "CA" per question
✅ ALL options have logic field (CA for correct answer, specific error description for distractors)
✅ Each distractor is based on COMMON MISTAKES specific to the sub-skill: ${subSkill || domain}
✅ Each distractor's logic explains a specific error related to ${subSkill || domain}
✅ Distractors reflect authentic student errors for this sub-skill, not generic mistakes
✅ CRITICAL: All 3 distractors represent DIFFERENT common mistakes for "${subSkill || domain}" (not variations of the same mistake)
✅ Each distractor's value is the result of making that specific mistake (e.g., if mistake is "added numerators", the distractor value should be the sum of numerators)
✅ Each solution is EXTREMELY DETAILED with ALL steps, calculations, and reasoning shown
✅ Each solution includes ALL intermediate calculations - no arithmetic operations are skipped
✅ Each solution shows ALL formula applications with explicit substitutions
✅ Each solution explains the reasoning behind each step
✅ Each solution is formatted with each step on a new line using \\n
✅ Easy questions have detailed solutions (3-5 steps minimum)
✅ Medium questions have comprehensive solutions (5-7 steps minimum)
✅ Hard questions have very detailed solutions (7-10+ steps minimum)
✅ Each question includes a "referenceLinks" array with 2-3 specific educational platform links
✅ Reference links are specific to the question's topic and skill, not generic grade-level links
✅ Reference links include proper URLs for IXL, Khan Academy, and/or Big Ideas Math
✅ All questions are clear, unambiguous, and age-appropriate
✅ No mathematical errors or logical contradictions
✅ Each scaffoldingExplanation includes copy question recommendations ONLY for the same difficulty level:
   - Easy questions include recommendations for 11 Easy copy questions only
   - Medium questions include recommendations for 11 Medium copy questions only
   - Hard questions include recommendations for 6 Hard copy questions only
✅ Copy question recommendations are specifically tailored for struggling ${gradeDisplay} students
✅ Recommendations account for reading level and use age-appropriate vocabulary for ${gradeDisplay}
✅ Recommendations provide specific parameter ranges/values that are appropriate for struggling learners
✅ All recommendations err on the side of simplicity rather than complexity for struggling students

CRITICAL FINAL REMINDER:
${notes ? `- ⚠️ CRITICAL: You MUST strictly follow ALL instructions from the "Additional Notes/Instructions" section. These notes are MANDATORY and must be incorporated into all ${totalQuestions} questions.
${notes.toLowerCase().includes('variation') || notes.toLowerCase().includes('1 on') || notes.toLowerCase().includes('one on') || /\d+\s+(?:on|for|about)/i.test(notes) ? `- ⚠️ CRITICAL: If Notes specify variations within difficulty levels (e.g., "Easy: 2 questions, 1 on addition and 1 on subtraction"), you MUST generate questions that exactly match those variations. Each variation must be clearly represented, and variations should be applied consistently across all sets.` : ''}` : ''}
- You MUST return EXACTLY ${totalQuestions} questions in the JSON array (${questionCounts.easy} Easy, ${questionCounts.medium} Medium, ${questionCounts.hard} Hard in that order)
- The ${totalQuestions} questions MUST show proper scaffolding with subtle progression
- ALL concepts of the sub-skill MUST be covered across the ${totalQuestions} questions
${!isDefaultCount ? `- When generating multiple questions of the same difficulty, ensure they are variations that test different aspects while maintaining that difficulty level` : ''}
- Each question MUST have EXACTLY 4 options - NO MORE, NO LESS
- Each solution MUST have steps on SEPARATE LINES using \\n - do NOT put multiple steps on the same line
- Solution format must be: "Step 1: ...\\nStep 2: ...\\nStep 3: ..." (with \\n between each step)
- Solutions MUST be EXTREMELY DETAILED - show ALL calculations, ALL substitutions, ALL reasoning
- Easy questions: minimum 3-5 detailed steps
- Medium questions: minimum 5-7 detailed steps  
- Hard questions: minimum 7-10+ detailed steps
- DO NOT skip any arithmetic operations - show every calculation explicitly
- DO NOT skip formula applications - show formula, substitution, then calculation
- DO NOT skip explanations - explain why each step is taken
- Verify scaffolding: Easy should be easy, Medium should be moderate (not forced application), Hard should be complex (not forced analysis)
- Verify concept coverage: All key aspects of the sub-skill are addressed across the ${totalQuestions} questions
- Verify that all ${totalQuestions} questions align with the curriculum standards and grade level
- Verify that all ${totalQuestions} questions target the specified domain and sub-skill
${standardCode ? `- Verify that all ${totalQuestions} questions align with standard code: ${standardCode}` : ''}
- Count your questions: The array must have exactly ${totalQuestions} elements, no more, no less
${!isDefaultCount ? `- Verify question distribution: ${questionCounts.easy} Easy, ${questionCounts.medium} Medium, ${questionCounts.hard} Hard` : ''}
- Count options in each question: Each question must have exactly 4 options
- Verify before submitting: Check that your JSON array contains exactly ${totalQuestions} question objects
- Verify before submitting: Check that each question has exactly 4 options in its options array
- Verify before submitting: Check that ALL options have a "logic" field (CA for correct, error description for distractors)
- Verify before submitting: Check that each distractor's logic describes a COMMON MISTAKE specific to the sub-skill: ${subSkill || domain}
- Verify before submitting: Check that each solution has steps separated by \\n (newline characters)
- Verify before submitting: Check that each solution is EXTREMELY DETAILED with all calculations shown
- Verify before submitting: Check that Easy questions have at least 3-5 steps, Medium have 5-7 steps, Hard have 7-10+ steps
- Verify before submitting: Check that no arithmetic operations are skipped - all calculations are shown
- Verify before submitting: Check that all formula applications show the formula, substitutions, and calculations
- Verify before submitting: Check that scaffolding progression is clear and natural
- The array must start with [ and end with ]
- DO NOT return fewer than ${totalQuestions} questions
- DO NOT return more than ${totalQuestions} questions
- DO NOT add extra options or remove options - the count must match exactly
- DO NOT put multiple solution steps on the same line - each step MUST be on its own line with \\n`

  // Build user prompt
  const scaffoldingText = isDefaultCount
    ? `1. Generate exactly ${totalQuestions} questions: ONE Easy, ONE Medium, ONE Hard (${setOfQuestionsNum} set${setOfQuestionsNum > 1 ? 's' : ''})`
    : `1. Generate exactly ${totalQuestions} questions: ${questionCounts.easy} Easy, ${questionCounts.medium} Medium, ${questionCounts.hard} Hard (${setOfQuestionsNum} set${setOfQuestionsNum > 1 ? 's' : ''} - ${baseQuestionCounts.easy} Easy, ${baseQuestionCounts.medium} Medium, ${baseQuestionCounts.hard} Hard per set)`
  
  const userPrompt = `Generate ${totalQuestions} original base questions with proper scaffolding across difficulty levels for the following specifications:

CURRICULUM ALIGNMENT:
- State Standards: ${stateStandards}
- Grade Level: ${gradeDisplay}
- Domain: ${domain}
${subSkill ? `- Sub-Skill: ${subSkill}` : '- Sub-Skill: General concepts within the domain'}
${standardCode ? `- Standard Code: ${standardCode}` : ''}
- Set(s) of Questions: ${setOfQuestions} (1 set = 1 Easy + 1 Medium + 1 Hard)
- Total questions to generate: ${totalQuestions} (${questionCounts.easy} Easy, ${questionCounts.medium} Medium, ${questionCounts.hard} Hard)
- Relevant Subskills: ${subskillsText}
${notes ? `\n\n⚠️ CRITICAL: ADDITIONAL NOTES/INSTRUCTIONS (MUST BE FOLLOWED):\n${notes}\n\nIMPORTANT: The instructions above in the "Additional Notes/Instructions" section are MANDATORY and must be strictly followed when generating all ${totalQuestions} questions. These notes take precedence and should guide your question generation process. Ensure that every aspect mentioned in the notes is incorporated into the generated questions.\n` : ''}

SCAFFOLDING REQUIREMENTS:
${scaffoldingText}
${setOfQuestionsNum > 1 ? `
IMPORTANT - SETS OF QUESTIONS:
- You are generating ${setOfQuestionsNum} SET(S) of questions
- Each set contains: ${baseQuestionCounts.easy} Easy, ${baseQuestionCounts.medium} Medium, ${baseQuestionCounts.hard} Hard question(s)
- Total: ${questionCounts.easy} Easy, ${questionCounts.medium} Medium, ${questionCounts.hard} Hard questions
- Questions within the same set should be related and show progression
- Questions across sets should be variations that test different aspects of the sub-skill
- Order: All Easy questions first (Set 1 Easy, Set 2 Easy, etc.), then all Medium, then all Hard
` : ''}
2. The ${totalQuestions} questions must show clear but subtle progression
3. Questions within the same difficulty level should show variation while maintaining that difficulty level
4. Questions should build upon previous questions of the same or lower difficulty level
5. ALL concepts related to the sub-skill must be covered across the ${totalQuestions} questions
6. Each question should address a different aspect or application of the sub-skill

DIFFICULTY LEVEL GUIDELINES:
- EASY: Basic understanding/recall, single-step or simple problems. DO NOT force real-world scenarios unless sub-skill demands it.
- MEDIUM: Moderate complexity, 2-3 steps, deeper understanding. DO NOT automatically use "application" unless sub-skill naturally involves real-world scenarios.
- HARD: Complex reasoning, multi-step, synthesis. DO NOT automatically use "analysis" unless sub-skill naturally requires it.

REQUIREMENTS FOR ALL ${totalQuestions} QUESTIONS:
${notes ? `0. ⚠️ CRITICAL: You MUST strictly follow ALL instructions provided in the "Additional Notes/Instructions" section. These notes are MANDATORY and take precedence. Every requirement, constraint, format specification, or instruction in the notes MUST be incorporated into all ${totalQuestions} questions.
   - If the Notes specify variations within a difficulty level (e.g., "Easy: 2 questions, 1 on addition and 1 on subtraction"), you MUST generate questions that match those exact variations
   - Each variation must be clearly represented in the generated questions
   - Variations should be applied consistently across all sets if multiple sets are requested
   - The question distribution must match what is specified in the Notes (e.g., if Notes say "Easy: 2 questions, 1 on addition and 1 on subtraction", then generate exactly 2 Easy questions per set: one clearly focused on addition, one clearly focused on subtraction)` : ''}
1. Each question must be ORIGINAL (not a variation of existing questions)
2. Questions must align with ${stateStandards} standards for ${gradeDisplay}
3. Questions must focus on ${domain}${subSkill ? ', specifically targeting ' + subSkill : ''}
${standardCode ? `4. Questions must align with standard code: ${standardCode}` : '4. Questions should be appropriate for the specified grade level and domain'}
5. Each question must have exactly 4 options
6. CRITICAL: ALL options (including correct answer) MUST have a "logic" field
7. CRITICAL: ALL incorrect options MUST be based on COMMON MISTAKES students make for the sub-skill: ${subSkill || domain}
8. CRITICAL: The logic for each distractor MUST explain a specific error related to ${subSkill || domain}
9. Each question must include a COMPLETE, EXTREMELY DETAILED step-by-step solution
10. Solutions must show ALL steps, ALL calculations, ALL substitutions, and ALL reasoning
11. Solutions must be formatted with each step on a new line using \\n
12. Easy questions must have at least 3-5 detailed steps
13. Medium questions must have at least 5-7 detailed steps
14. Hard questions must have at least 7-10+ detailed steps
15. DO NOT skip any arithmetic operations - show every calculation explicitly
16. The ${totalQuestions} questions together must cover ALL key concepts of the sub-skill
${!isDefaultCount ? `17. When generating multiple questions of the same difficulty level, ensure they are variations that test different aspects or applications while maintaining the same difficulty level` : ''}
17. CRITICAL: Each question MUST include a "difficultyReasoning" field explaining why it is classified as Easy, Medium, or Hard
18. CRITICAL: Each question MUST include a "scaffoldingExplanation" field explaining how it builds on previous questions and prepares for subsequent ones
19. The "difficultyReasoning" should explain the cognitive demands, complexity level, and why this question fits the difficulty classification
20. The "scaffoldingExplanation" should explain:
   - The pedagogical progression: how the Easy question establishes foundation, how Medium builds on Easy, and how Hard synthesizes concepts from both
   - COPY QUESTION RECOMMENDATIONS (CRITICAL): Provide specific recommendations for generating copy questions (variations) of this base question
   - IMPORTANT: Each question's scaffoldingExplanation should ONLY contain recommendations for copy questions of the SAME difficulty level:
     * Easy questions → recommendations for 11 Easy copy questions only
     * Medium questions → recommendations for 11 Medium copy questions only
     * Hard questions → recommendations for 6 Hard copy questions only
   - IMPORTANT CONTEXT: These questions are for students who struggle in mathematics. Recommendations must be appropriate for struggling learners at ${gradeDisplay} level
   - READING LEVEL CONSIDERATION: Recommendations must account for the reading level of ${gradeDisplay} students - use age-appropriate vocabulary and sentence complexity
   - For the appropriate difficulty level, provide specific, actionable recommendations including:
     * Parameter ranges/values (e.g., number ranges, coefficient sizes, fraction complexity)
     * Complexity limits appropriate for struggling students
     * Specific examples of what to vary (e.g., "Use numbers 10-30", "Use single-digit coefficients", "Use like denominators only")
     * Considerations for reading level and mathematical vocabulary
   - Examples of good recommendations:
     * Easy question (Prime factorization, ${gradeDisplay}): "11 Easy copy questions: Use numbers 12-50 with 2-3 prime factors. Keep numbers small and familiar. Use simple vocabulary appropriate for ${gradeDisplay}."
     * Medium question (Area problems, ${gradeDisplay}): "11 Medium copy questions: Use whole numbers 10-50 or simple decimals (0.5, 0.25). Maintain 2-3 step complexity. Keep language clear and accessible for ${gradeDisplay}."
     * Hard question (Fraction addition, ${gradeDisplay}): "6 Hard copy questions: Use unlike denominators with no common factors, but keep denominators under 20. Maintain multi-step complexity. Ensure all language is age-appropriate for ${gradeDisplay}."
   - CRITICAL: All recommendations must be appropriate for struggling ${gradeDisplay} students - err on the side of simpler rather than more complex

Generate ${totalQuestions} high-quality, curriculum-aligned base questions with proper scaffolding now.`

  try {
    // Calculate tokens needed (generating questions with scaffolding)
    const tokensPerQuestion = 600 // Base questions may need more tokens
    let tokensNeeded = Math.max(3000, tokensPerQuestion * totalQuestions) // Dynamic question count
    tokensNeeded = Math.min(16000, tokensNeeded) // Cap at reasonable maximum
    
    // Set temperature for base question generation (slightly higher for creativity)
    const temperature = 0.8
    
    // Use unified AI client
    let content: string
    try {
      content = await generateWithAI(
        systemPrompt,
        userPrompt,
        model,
        temperature,
        tokensNeeded
      )
    } catch (error: any) {
      // If model is not available, fallback to gpt-4o (for OpenAI models) or gemini-1.5-pro (for Gemini)
      if (error?.message?.includes('model') || error?.code === 'model_not_found') {
        const provider = getAIProvider(model)
        let fallbackModel = 'gpt-4o'
        if (provider === 'gemini') {
          fallbackModel = 'gemini-1.5-pro'
        }
        console.warn(`${model} not available, falling back to ${fallbackModel}`)
        content = await generateWithAI(
          systemPrompt,
          userPrompt,
          fallbackModel,
          temperature,
          tokensNeeded
        )
      } else {
        throw error
      }
    }
    
    if (!content || content.trim().length === 0) {
      throw new Error('AI returned empty content')
    }
    
    // Parse JSON from response
    let jsonContent = content.trim()
    
    // Remove markdown code blocks if present
    if (jsonContent.startsWith('```json')) {
      jsonContent = jsonContent.replace(/^```json\s*/, '').replace(/\s*```$/, '')
    } else if (jsonContent.startsWith('```')) {
      jsonContent = jsonContent.replace(/^```\s*/, '').replace(/\s*```$/, '')
    }
    
    // Extract JSON array
    const jsonMatch = jsonContent.match(/\[[\s\S]*\]/)
    if (jsonMatch) {
      jsonContent = jsonMatch[0]
    }
    
    let questions
    try {
      questions = JSON.parse(jsonContent)
    } catch (parseError) {
      console.error('JSON parse error:', parseError)
      console.error('Content:', jsonContent)
      throw new Error('Failed to parse JSON response from GPT')
    }
    
    if (!Array.isArray(questions)) {
      throw new Error('AI did not return an array of questions')
    }
    
    // Validate and clean questions first, then check length
    const validatedQuestions = questions
      .filter((q: any) => q && typeof q === 'object')
      .map((q: any, index: number) => {
        // Determine which set and difficulty this question should be based on position
        // AI returns questions in order: All Easy (Set 1 Easy, Set 2 Easy, ...), then all Medium, then all Hard
        // We need to assign set numbers based on position within each difficulty group
        let expectedDifficulty = 'Easy'
        let setNumber = 1
        
        if (index < questionCounts.easy) {
          // Easy questions: index 0 to questionCounts.easy - 1
          expectedDifficulty = 'Easy'
          setNumber = Math.floor(index / baseQuestionCounts.easy) + 1
        } else if (index < questionCounts.easy + questionCounts.medium) {
          // Medium questions: index questionCounts.easy to questionCounts.easy + questionCounts.medium - 1
          expectedDifficulty = 'Medium'
          const mediumIndex = index - questionCounts.easy
          setNumber = Math.floor(mediumIndex / baseQuestionCounts.medium) + 1
        } else {
          // Hard questions: remaining indices
          expectedDifficulty = 'Hard'
          const hardIndex = index - questionCounts.easy - questionCounts.medium
          setNumber = Math.floor(hardIndex / baseQuestionCounts.hard) + 1
        }
        
        // Use AI-provided difficulty if valid, otherwise use expected difficulty based on position
        let difficulty = q.difficulty || ''
        if (!difficulty || !['Easy', 'Medium', 'Hard'].includes(difficulty)) {
          difficulty = expectedDifficulty
        }
        
        // Ensure required fields
        const question: any = {
          difficulty: difficulty,
          question: q.question || `Question ${index + 1}`,
          options: Array.isArray(q.options) ? q.options : [],
          image: q.image || '',
          solution: q.solution || '',
          difficultyReasoning: q.difficultyReasoning || '',
          scaffoldingExplanation: q.scaffoldingExplanation || '',
          setNumber: setNumber,
          referenceLinks: Array.isArray(q.referenceLinks) ? q.referenceLinks : []
        }
        
        // Ensure exactly 4 options
        if (question.options.length !== 4) {
          // Pad or trim to 4 options
          while (question.options.length < 4) {
            question.options.push({
              text: `Option ${String.fromCharCode(65 + question.options.length)}`,
              logic: 'Placeholder'
            })
          }
          question.options = question.options.slice(0, 4)
        }
        
        // Ensure at least one CA
        const hasCA = question.options.some((opt: any) => opt.logic === 'CA')
        if (!hasCA && question.options.length > 0) {
          question.options[0].logic = 'CA'
        }
        
        return question
      })
    
    if (validatedQuestions.length === 0) {
      throw new Error('No valid questions were generated. Please check the parameters and try again.')
    }
    
    // Ensure we have exactly the expected number of questions after validation
    if (validatedQuestions.length !== totalQuestions) {
      const originalCount = questions.length
      const filteredCount = originalCount - validatedQuestions.length
      const expectedText = `${questionCounts.easy} Easy, ${questionCounts.medium} Medium, ${questionCounts.hard} Hard`
      const errorMsg = filteredCount > 0
        ? `Expected exactly ${totalQuestions} valid questions (${expectedText}), but received ${originalCount} items with ${filteredCount} invalid item(s) filtered out, leaving ${validatedQuestions.length} valid question(s)`
        : `Expected exactly ${totalQuestions} questions (${expectedText}), but only ${validatedQuestions.length} were generated`
      throw new Error(errorMsg)
    }
    
    // Verify difficulty distribution
    const easyCount = validatedQuestions.filter((q: any) => q.difficulty === 'Easy').length
    const mediumCount = validatedQuestions.filter((q: any) => q.difficulty === 'Medium').length
    const hardCount = validatedQuestions.filter((q: any) => q.difficulty === 'Hard').length
    
    if (easyCount !== questionCounts.easy || mediumCount !== questionCounts.medium || hardCount !== questionCounts.hard) {
      throw new Error(`Expected ${questionCounts.easy} Easy, ${questionCounts.medium} Medium, ${questionCounts.hard} Hard questions, but received ${easyCount} Easy, ${mediumCount} Medium, ${hardCount} Hard`)
    }
    
    // Sort by set number first, then by difficulty within each set
    const difficultyOrder = { 'Easy': 0, 'Medium': 1, 'Hard': 2 }
    validatedQuestions.sort((a: any, b: any) => {
      // First sort by set number
      const setA = a.setNumber || 999
      const setB = b.setNumber || 999
      if (setA !== setB) {
        return setA - setB
      }
      // Within same set, sort by difficulty
      const orderA = difficultyOrder[a.difficulty as keyof typeof difficultyOrder] ?? 999
      const orderB = difficultyOrder[b.difficulty as keyof typeof difficultyOrder] ?? 999
      return orderA - orderB
    })
    
    // Return all 3 questions
    return validatedQuestions
  } catch (error: any) {
    console.error('Error in generateBaseQuestionsWithGPT:', error)
    throw error
  }
}

