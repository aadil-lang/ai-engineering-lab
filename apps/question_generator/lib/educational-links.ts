// Educational platform link generation utility

export interface EducationalLink {
  platform: string;
  url: string;
  label: string;
  icon?: string;
}

/**
 * Generates educational platform links based on grade, domain, and subskill
 */
export function generateEducationalLinks(
  grade: string,
  domain: string,
  subSkill: string,
  stateStandards?: string,
  standardCode?: string
): EducationalLink[] {
  const links: EducationalLink[] = [];
  
  // Normalize grade for URL construction
  const gradeNum = grade === 'High School' ? '9' : grade.replace('Grade ', '').replace('grade ', '');
  
  // Generate IXL link
  const ixlLink = generateIXLLink(gradeNum, domain, subSkill);
  if (ixlLink) {
    links.push({
      platform: 'IXL',
      url: ixlLink,
      label: 'Practice on IXL',
      icon: '📚'
    });
  }
  
  // Generate Khan Academy link
  const khanLink = generateKhanAcademyLink(gradeNum, domain, subSkill);
  if (khanLink) {
    links.push({
      platform: 'Khan Academy',
      url: khanLink,
      label: 'Learn on Khan Academy',
      icon: '🎓'
    });
  }
  
  // Generate Big Ideas Math link
  const bimLink = generateBigIdeasMathLink(gradeNum, domain, subSkill);
  if (bimLink) {
    links.push({
      platform: 'Big Ideas Math',
      url: bimLink,
      label: 'Big Ideas Math',
      icon: '📖'
    });
  }
  
  return links;
}

/**
 * Generates IXL link based on grade and subskill
 * IXL URL structure: https://www.ixl.com/math/grade-X/subskill-slug
 */
function generateIXLLink(grade: string, domain: string, subSkill: string): string | null {
  try {
    // Convert subskill to URL-friendly slug
    const subSkillSlug = subSkill.toLowerCase()
      .replace(/\s+/g, '-')
      .replace(/[^a-z0-9-]/g, '')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '');
    
    // Map grade to IXL grade format
    const gradeMap: Record<string, string> = {
      'K': 'kindergarten',
      '0': 'kindergarten',
      '1': 'first-grade',
      '2': 'second-grade',
      '3': 'third-grade',
      '4': 'fourth-grade',
      '5': 'fifth-grade',
      '6': 'sixth-grade',
      '7': 'seventh-grade',
      '8': 'eighth-grade',
      '9': 'algebra-1',
      '10': 'geometry',
      '11': 'algebra-2',
      '12': 'precalculus'
    };
    
    const gradeSlug = gradeMap[grade] || `grade-${grade}`;
    
    // Return search URL if we can't construct a direct link
    if (!subSkillSlug) {
      return `https://www.ixl.com/math/${gradeSlug}`;
    }
    
    return `https://www.ixl.com/math/${gradeSlug}/${subSkillSlug}`;
  } catch (error) {
    return null;
  }
}

/**
 * Generates Khan Academy link based on grade and subskill
 * Khan Academy URL structure varies by grade and topic
 */
function generateKhanAcademyLink(grade: string, domain: string, subSkill: string): string | null {
  try {
    // Map grade to Khan Academy grade path
    const gradeMap: Record<string, string> = {
      'K': 'early-math',
      '0': 'early-math',
      '1': 'cc-1st-grade-math',
      '2': 'cc-2nd-grade-math',
      '3': 'cc-third-grade-math',
      '4': 'cc-fourth-grade-math',
      '5': 'cc-fifth-grade-math',
      '6': 'cc-6th-grade-math',
      '7': 'cc-7th-grade-math',
      '8': 'cc-8th-grade-math',
      '9': 'algebra',
      '10': 'geometry',
      '11': 'algebra2',
      '12': 'precalculus'
    };
    
    const gradePath = gradeMap[grade] || `cc-${grade}-grade-math`;
    
    // Convert subskill to topic slug
    const topicSlug = subSkill.toLowerCase()
      .replace(/\s+/g, '-')
      .replace(/[^a-z0-9-]/g, '')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '');
    
    // Return search URL if we can't construct a direct link
    if (!topicSlug) {
      return `https://www.khanacademy.org/math/${gradePath}`;
    }
    
    return `https://www.khanacademy.org/math/${gradePath}/${topicSlug}`;
  } catch (error) {
    return null;
  }
}

/**
 * Generates Big Ideas Math link based on grade and subskill
 * Big Ideas Math URL structure varies by grade
 */
function generateBigIdeasMathLink(grade: string, domain: string, subSkill: string): string | null {
  try {
    // Big Ideas Math uses a different structure
    // For now, return a general grade-level link
    const gradeMap: Record<string, string> = {
      'K': 'k',
      '1': '1',
      '2': '2',
      '3': '3',
      '4': '4',
      '5': '5',
      '6': '6',
      '7': '7',
      '8': '8',
      '9': 'algebra-1',
      '10': 'geometry',
      '11': 'algebra-2',
      '12': 'precalculus'
    };
    
    const gradeSlug = gradeMap[grade] || grade;
    
    // Big Ideas Math doesn't have direct subskill links in their public URL structure
    // Return the grade-level resource page
    return `https://www.bigideasmath.com/students/?level=library&grade=${gradeSlug}`;
  } catch (error) {
    return null;
  }
}

