export type Difficulty = "Easy" | "Medium" | "Hard";
export type QuestionType = "multiple_choice" | "short_answer" | "numeric" | "word_problem";
export type CognitiveLevel = "remember" | "understand" | "apply" | "analyze" | "evaluate" | "create";

export type StateCode = 
  | "CA" // California
  | "TX" // Texas
  | "NY" // New York
  | "FL" // Florida
  | "VA" // Virginia
  | "CCSS"; // Common Core (default)

export interface Question {
  question_id: string;
  state: string;
  grade: string;
  domain: string;
  sub_skill: string;
  standard_code: string;
  difficulty: Difficulty;
  question_text: string;
  question_type: QuestionType;
  answer: string;
  options?: string[]; // Required for multiple_choice
  explanation: string;
  estimated_time: string;
  cognitive_level: CognitiveLevel;
}

export interface QuestionGenerationRequest {
  state: StateCode;
  grade: string;
  sub_skill: string;
  difficulty: Difficulty;
  quantity: number;
}

export interface QuestionGenerationResponse {
  questions: Question[];
  success: boolean;
  error?: string;
}

