"use client";

import { Question } from "@/types/question";

interface QuestionDisplayProps {
  questions: Question[];
}

export default function QuestionDisplay({ questions }: QuestionDisplayProps) {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
        Generated Questions ({questions.length})
      </h2>
      
      {questions.map((question, index) => (
        <div
          key={question.question_id}
          className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm"
        >
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Question {index + 1}
              </h3>
              <div className="flex flex-wrap gap-2 mt-2">
                <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded">
                  {question.grade}
                </span>
                <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded">
                  {question.difficulty}
                </span>
                <span className="px-2 py-1 text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200 rounded">
                  {question.domain}
                </span>
                <span className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 rounded">
                  {question.cognitive_level}
                </span>
              </div>
            </div>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              ID: {question.question_id}
            </span>
          </div>

          <div className="space-y-4">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Sub-skill: <span className="font-medium">{question.sub_skill}</span>
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Standard: <span className="font-medium">{question.standard_code}</span>
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Estimated time: <span className="font-medium">{question.estimated_time} minutes</span>
              </p>
            </div>

            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
              <p className="text-base font-medium text-gray-900 dark:text-gray-100 mb-2">
                Question:
              </p>
              <p className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                {question.question_text}
              </p>
            </div>

            {question.question_type === "multiple_choice" && question.options && (
              <div>
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Options:
                </p>
                <ul className="space-y-2">
                  {question.options.map((option, optIndex) => {
                    const isCorrect = option === question.answer;
                    return (
                      <li
                        key={optIndex}
                        className={`p-3 rounded-lg border ${
                          isCorrect
                            ? "bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800"
                            : "bg-white border-gray-200 dark:bg-gray-800 dark:border-gray-700"
                        }`}
                      >
                        <span className="font-medium mr-2">
                          {String.fromCharCode(65 + optIndex)}.
                        </span>
                        <span className={isCorrect ? "font-semibold text-green-700 dark:text-green-300" : "text-gray-700 dark:text-gray-300"}>
                          {option}
                          {isCorrect && (
                            <span className="ml-2 text-xs">✓ Correct</span>
                          )}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}

            {question.question_type !== "multiple_choice" && (
              <div>
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Answer:
                </p>
                <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
                  <p className="font-semibold text-green-700 dark:text-green-300">
                    {question.answer}
                  </p>
                </div>
              </div>
            )}

            <div>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Explanation:
              </p>
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <p className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                  {question.explanation}
                </p>
              </div>
            </div>
          </div>
        </div>
      ))}

      <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
          <strong>Export JSON:</strong>
        </p>
        <pre className="text-xs bg-gray-900 dark:bg-black text-gray-100 p-4 rounded-lg overflow-x-auto">
          {JSON.stringify(questions, null, 2)}
        </pre>
      </div>
    </div>
  );
}

