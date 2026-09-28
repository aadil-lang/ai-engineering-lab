// Sub-skills organized by grade level and domain
export const SUB_SKILLS: Record<string, Record<string, string[]>> = {
  "K-2": {
    "Number Sense": [
      "Counting to 100",
      "Number recognition",
      "Comparing numbers",
      "Place value (ones, tens)",
      "Number patterns"
    ],
    "Operations": [
      "Addition within 20",
      "Subtraction within 20",
      "Addition word problems",
      "Subtraction word problems"
    ],
    "Geometry": [
      "Identifying shapes",
      "2D shapes",
      "3D shapes",
      "Shape attributes"
    ],
    "Measurement": [
      "Length comparison",
      "Time (hours, half-hours)",
      "Money (coins)"
    ]
  },
  "3-5": {
    "Operations": [
      "Multiplication facts",
      "Division facts",
      "Multi-digit multiplication",
      "Multi-digit division",
      "Order of operations"
    ],
    "Fractions": [
      "Understanding fractions",
      "Comparing fractions",
      "Adding fractions",
      "Subtracting fractions",
      "Multiplying fractions",
      "Dividing fractions",
      "Equivalent fractions"
    ],
    "Decimals": [
      "Decimal place value",
      "Comparing decimals",
      "Adding decimals",
      "Subtracting decimals",
      "Multiplying decimals",
      "Dividing decimals"
    ],
    "Geometry": [
      "Area and perimeter",
      "Angles",
      "Symmetry",
      "Coordinate plane"
    ],
    "Data Analysis": [
      "Reading graphs",
      "Creating graphs",
      "Mean, median, mode",
      "Probability basics"
    ]
  },
  "6-8": {
    "Ratios & Proportions": [
      "Understanding ratios",
      "Equivalent ratios",
      "Unit rates",
      "Proportions",
      "Percent problems"
    ],
    "Number Systems": [
      "Integers",
      "Rational numbers",
      "Absolute value",
      "Number line operations"
    ],
    "Algebra": [
      "Expressions",
      "Equations",
      "Inequalities",
      "Linear functions",
      "Slope and intercepts"
    ],
    "Statistics": [
      "Data collection",
      "Measures of center",
      "Measures of spread",
      "Scatter plots",
      "Correlation"
    ],
    "Probability": [
      "Simple probability",
      "Compound probability",
      "Independent events",
      "Dependent events"
    ],
    "Geometry": [
      "Area formulas",
      "Volume formulas",
      "Pythagorean theorem",
      "Transformations",
      "Similarity and congruence"
    ]
  },
  "9-12": {
    "Algebra I": [
      "Linear equations",
      "Systems of equations",
      "Quadratic equations",
      "Polynomials",
      "Factoring",
      "Exponential functions"
    ],
    "Algebra II": [
      "Advanced polynomials",
      "Rational expressions",
      "Radical expressions",
      "Logarithms",
      "Complex numbers",
      "Sequences and series"
    ],
    "Geometry": [
      "Proofs",
      "Triangle properties",
      "Circle theorems",
      "Area and volume",
      "Coordinate geometry"
    ],
    "Trigonometry": [
      "Right triangle trigonometry",
      "Unit circle",
      "Trigonometric identities",
      "Graphing trig functions",
      "Law of sines and cosines"
    ],
    "Pre-Calculus": [
      "Functions and graphs",
      "Polynomial functions",
      "Rational functions",
      "Exponential and logarithmic functions",
      "Trigonometric functions",
      "Conic sections"
    ],
    "Calculus": [
      "Limits",
      "Derivatives",
      "Applications of derivatives",
      "Integrals",
      "Applications of integrals",
      "Differential equations"
    ],
    "Statistics": [
      "Descriptive statistics",
      "Probability distributions",
      "Hypothesis testing",
      "Confidence intervals",
      "Regression analysis"
    ]
  }
};

export function getGradeRange(grade: string): string {
  // Handle "High School" string input
  if (grade.toLowerCase() === 'high school' || grade === 'High School') {
    return "9-12";
  }
  
  const gradeNum = parseInt(grade);
  if (gradeNum >= 0 && gradeNum <= 2) return "K-2";
  if (gradeNum >= 3 && gradeNum <= 5) return "3-5";
  if (gradeNum >= 6 && gradeNum <= 8) return "6-8";
  if (gradeNum >= 9 && gradeNum <= 12) return "9-12";
  return "K-2";
}

export function getSubSkillsForGrade(grade: string): Record<string, string[]> {
  const gradeRange = getGradeRange(grade);
  return SUB_SKILLS[gradeRange] || SUB_SKILLS["K-2"];
}

export const STATE_OPTIONS = [
  { value: "CCSS", label: "Common Core State Standards (CCSS)" },
  { value: "CA", label: "California (CA-CCSS)" },
  { value: "TX", label: "Texas (TEKS)" },
  { value: "NY", label: "New York (NYSED)" },
  { value: "FL", label: "Florida (B.E.S.T.)" },
  { value: "VA", label: "Virginia (VA SOL)" }
];

export const GRADE_OPTIONS = [
  { value: "K", label: "Kindergarten" },
  ...Array.from({ length: 8 }, (_, i) => ({ 
    value: String(i + 1), 
    label: `Grade ${i + 1}` 
  })),
  { value: "High School", label: "High School" }
];

export const DIFFICULTY_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "Easy", label: "Easy (Foundational)" },
  { value: "Medium", label: "Medium (Application)" },
  { value: "Hard", label: "Hard (Advanced)" }
];

