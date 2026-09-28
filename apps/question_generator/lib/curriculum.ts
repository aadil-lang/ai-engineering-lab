import { getGradeRange, SUB_SKILLS } from './subskills'

/**
 * Loads relevant subskills for a given grade and curriculum
 * @param grade - The grade level (e.g., "K", "1", "2", etc.)
 * @param curriculum - The curriculum standard (e.g., "CCSS", "CA", "TX", etc.)
 * @returns Array of subskill strings
 */
export function loadCurriculumSubskills(grade: string, curriculum: string): string[] {
  const gradeRange = getGradeRange(grade)
  const gradeSubskills = SUB_SKILLS[gradeRange] || SUB_SKILLS["K-2"]
  
  // Flatten all subskills from all domains for the grade range
  const allSubskills: string[] = []
  for (const domain in gradeSubskills) {
    allSubskills.push(...gradeSubskills[domain])
  }
  
  return allSubskills
}

